import json
import queue
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
import vgamepad as vg
from PIL import Image, ImageTk

from ..config.paths import CALIB_FILE, MODEL_FILE
from ..gestures.engine import GestureEngine
from .theme import Theme
from .widgets import GDBar, GDButton, GDCard, GDStatusDot, SectionHeader


# ---------------------------------------------------------------------------
# MediaPipe aliases
# ---------------------------------------------------------------------------

BaseOptions           = mp.tasks.BaseOptions
HandLandmarker        = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HAND_CONNECTIONS = [
    (0, 1),  (1, 2),  (2, 3),  (3, 4),
    (0, 5),  (5, 6),  (6, 7),  (7, 8),
    (5, 9),  (9, 10), (10, 11),(11, 12),
    (9, 13), (13, 14),(14, 15),(15, 16),
    (13, 17),(17, 18),(18, 19),(19, 20),
    (0, 17),
]

DISPLAY_W  = 480
DISPLAY_H  = 360
FPS_WINDOW = 30   # rolling window size for FPS averaging


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_calib() -> dict:
    """Load calibration data from disk, returning an empty dict on failure."""
    if CALIB_FILE.exists():
        try:
            with open(CALIB_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _draw_landmarks(frame: np.ndarray, result) -> None:
    """Draw hand skeleton overlay onto *frame* in-place."""
    if not (result and result.hand_landmarks):
        return

    h, w = frame.shape[:2]
    for i, landmarks in enumerate(result.hand_landmarks):
        raw   = result.handedness[i][0].display_name
        color = (60, 200, 100) if raw == "Right" else (70, 130, 220)
        pts   = [(int(p.x * w), int(p.y * h)) for p in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], color, 2)
        for pt in pts:
            cv2.circle(frame, pt, 4, color, -1)


# ---------------------------------------------------------------------------
# _GamepadState
# ---------------------------------------------------------------------------

class _GamepadState:
    """
    Wraps a ``vg.VX360Gamepad`` and tracks the last-sent button states so
    press / release are only called when a button actually changes (~30% fewer
    vgamepad calls).
    """

    def __init__(self, gp: vg.VX360Gamepad) -> None:
        self._gp      = gp
        self._buttons: dict = {}

    def update(self, state: dict) -> None:
        gp = self._gp
        gp.left_joystick_float(x_value_float=state["steering"], y_value_float=0.0)
        gp.right_trigger_float(value_float=state["throttle"])
        gp.left_trigger_float(value_float=state["brake"])

        for key, btn in [
            ("handbrake", vg.XUSB_BUTTON.XUSB_GAMEPAD_A),
            ("gear_up",   vg.XUSB_BUTTON.XUSB_GAMEPAD_B),
            ("gear_down", vg.XUSB_BUTTON.XUSB_GAMEPAD_X),
        ]:
            val = bool(state.get(key, False))
            if val != self._buttons.get(btn):
                (gp.press_button if val else gp.release_button)(btn)
                self._buttons[btn] = val

        gp.update()

    def reset(self) -> None:
        self._gp.reset()
        self._gp.update()
        self._buttons.clear()


# ---------------------------------------------------------------------------
# RuntimeScreen
# ---------------------------------------------------------------------------

class RuntimeScreen(tk.Frame):
    """Live driving screen: camera feed, gesture processing, gamepad output."""

    def __init__(
        self,
        parent,
        theme: Theme,
        settings,
        on_recalibrate,
        on_exit,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_root"])

        self._theme          = theme
        self._settings       = settings
        self._on_recalibrate = on_recalibrate
        self._on_exit        = on_exit

        self._paused     = False
        self._stop_event = threading.Event()

        self._smooth_steering = 0.0
        self._smooth_throttle = 0.0
        self._smooth_brake    = 0.0

        self._latest_result = None
        self._result_lock   = threading.Lock()
        self._timestamp     = 0

        self._fps_times: deque       = deque(maxlen=FPS_WINDOW)
        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)  # maxsize=1: always the latest frame

        self._cap:       Optional[cv2.VideoCapture] = None
        self._landmarker = None
        self._gp_state:  Optional[_GamepadState]   = None
        self._engine:    Optional[GestureEngine]    = None

        self._canvas_image_id = None   # reused Canvas image item
        self._last_fps  = -1           # cached FPS value — skip label.config() when unchanged
        self._last_conf = -1           # cached confidence value

        self._build()
        self.after(100, self._init_hardware)

    # -- layout ----------------------------------------------------------------

    def _build(self) -> None:
        t = self._theme
        c = t.colors

        SectionHeader(self, "GestureDrive is Running", t).pack(fill="x")

        body = tk.Frame(self, bg=c["bg_root"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_camera_panel(body, t, c)
        self._build_telemetry_panel(body, t, c)

        # Footer
        footer = tk.Frame(self, bg=c["bg_card_deep"])
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=(
                "vgamepad virtual Xbox controller active  ·  "
                "Press Recalibrate anytime  ·  Skippy"
            ),
            font=t.font_small,
            bg=c["bg_card_deep"], fg=c["text_muted"],
            pady=5,
        ).pack()

    def _build_camera_panel(self, body, t, c) -> None:
        left = GDCard(body, t)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._cam_canvas = tk.Canvas(
            left, width=DISPLAY_W, height=DISPLAY_H,
            bg="#111111", highlightthickness=0,
        )
        self._cam_canvas.pack(padx=10, pady=10)

        status_row = tk.Frame(left, bg=c["bg_card"])
        status_row.pack(fill="x", padx=10, pady=(0, 8))

        self._dot_left  = GDStatusDot(status_row, "Left hand",  t)
        self._dot_right = GDStatusDot(status_row, "Right hand", t)
        self._dot_left.pack(side="left",  padx=(0, 12))
        self._dot_right.pack(side="left", padx=(0, 12))

        self._fps_lbl = tk.Label(
            status_row, text="-- fps",
            font=t.font_mono, bg=c["bg_card"], fg=c["text_muted"],
        )
        self._fps_lbl.pack(side="right")

        self._conn_lbl = tk.Label(
            status_row, text="Gamepad: connecting…",
            font=t.font_small, bg=c["bg_card"], fg=c["warn"],
        )
        self._conn_lbl.pack(side="right", padx=(0, 12))

    def _build_telemetry_panel(self, body, t, c) -> None:
        right = tk.Frame(body, bg=c["bg_root"])
        right.pack(side="left", fill="y", ipadx=8)

        # Telemetry bars
        tele = GDCard(right, t)
        tele.pack(fill="x", pady=(0, 10), ipadx=12, ipady=12)

        tk.Label(tele, text="TELEMETRY",
                 font=t.font_label, bg=c["bg_card"], fg=c["text_muted"],
                 pady=6, padx=12).pack(anchor="w")

        self._bar_steer = GDBar(tele, "Steering", t, mode="center", color=c["accent"])
        self._bar_throt = GDBar(tele, "Throttle", t, mode="left",   color=c["ok"])
        self._bar_brake = GDBar(tele, "Brake",    t, mode="left",   color=c["error"])
        for bar in (self._bar_steer, self._bar_throt, self._bar_brake):
            bar.pack(fill="x", padx=12, pady=3)

        conf_row = tk.Frame(tele, bg=c["bg_card"])
        conf_row.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(conf_row, text="Confidence",
                 font=t.font_small, bg=c["bg_card"], fg=c["text_muted"]).pack(side="left")
        self._conf_lbl = tk.Label(conf_row, text="0%",
                                   font=t.font_mono, bg=c["bg_card"], fg=c["accent"])
        self._conf_lbl.pack(side="right")

        # Active gestures
        badge_row = GDCard(right, t)
        badge_row.pack(fill="x", pady=(0, 10), ipadx=12, ipady=8)

        tk.Label(badge_row, text="ACTIVE GESTURES",
                 font=t.font_label, bg=c["bg_card"], fg=c["text_muted"],
                 pady=4, padx=12).pack(anchor="w")

        badges = tk.Frame(badge_row, bg=c["bg_card"])
        badges.pack(fill="x", padx=12)

        self._badges: dict      = {}
        self._badge_state: dict = {}

        for key, label, color in [
            ("handbrake", "HANDBRAKE", c["warn"]),
            ("gear_up",   "GEAR ↑",    c["accent"]),
            ("gear_down", "GEAR ↓",    c["accent_alt"]),
        ]:
            lbl = tk.Label(badges, text=label,
                           font=t.font_label,
                           bg=c["border"], fg=c["text_muted"],
                           padx=10, pady=4)
            lbl.pack(side="left", padx=(0, 6), pady=4)
            self._badges[key]      = (lbl, color)
            self._badge_state[key] = False

        # Controls
        ctrl = GDCard(right, t)
        ctrl.pack(fill="x", ipadx=12, ipady=8)

        tk.Label(ctrl, text="CONTROLS",
                 font=t.font_label, bg=c["bg_card"], fg=c["text_muted"],
                 pady=6, padx=12).pack(anchor="w")

        self._pause_btn = GDButton(ctrl, "|| Pause",
                                    command=self._toggle_pause,
                                    style="secondary", theme=t)
        self._pause_btn.pack(fill="x", padx=12, pady=(0, 6))

        GDButton(ctrl, ">> Recalibrate",
                 command=self._on_recalibrate,
                 style="ghost", theme=t).pack(fill="x", padx=12, pady=(0, 6))

        GDButton(ctrl, "Exit",
                 command=self._do_exit,
                 style="danger", theme=t).pack(fill="x", padx=12)

    # -- hardware init ---------------------------------------------------------

    def _init_hardware(self) -> None:
        cam_idx = self._settings.camera_index
        try:
            self._cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_FPS,          30)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

            if not self._cap.isOpened():
                raise RuntimeError(f"Camera {cam_idx} not available")
            if not MODEL_FILE.exists():
                raise RuntimeError(f"MediaPipe model missing:\n{MODEL_FILE}")

            def _on_result(result, img, ts):
                with self._result_lock:
                    self._latest_result = result

            opts = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(MODEL_FILE)),
                running_mode=VisionRunningMode.LIVE_STREAM,
                num_hands=2,
                min_hand_detection_confidence=0.6,
                min_hand_presence_confidence=0.6,
                min_tracking_confidence=0.6,
                result_callback=_on_result,
            )
            self._landmarker = HandLandmarker.create_from_options(opts)

            gp = vg.VX360Gamepad()
            self._gp_state = _GamepadState(gp)
            self._conn_lbl.config(text="Virtual Gamepad Connected",
                                   fg=self._theme.colors["ok"])

            calib       = _load_calib()
            self._engine = GestureEngine(self._settings.as_dict(), calib)

            threading.Thread(target=self._capture_loop, daemon=True).start()
            self._poll_ui()

        except Exception as exc:
            messagebox.showerror("Initialisation Error", str(exc))
            self._conn_lbl.config(text=f"Error: {exc}",
                                   fg=self._theme.colors["error"])

    # -- capture thread --------------------------------------------------------

    def _capture_loop(self) -> None:
        """
        Background thread: captures frames, draws overlays, resizes them,
        converts colour space, then drops the result into the UI queue.
        All heavy work happens here, off the main thread.
        """
        while not self._stop_event.is_set():
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            cv2.flip(frame, 1, dst=frame)  # in-place mirror

            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            self._timestamp += 1
            try:
                self._landmarker.detect_async(mp_image, self._timestamp)
            except Exception:
                pass

            with self._result_lock:
                result = self._latest_result

            _draw_landmarks(frame, result)

            disp     = cv2.resize(frame, (DISPLAY_W, DISPLAY_H), interpolation=cv2.INTER_LINEAR)
            disp_rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)

            # Always keep only the latest frame (drop stale ones)
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._frame_queue.put_nowait((disp_rgb, result))
            except queue.Full:
                pass

    # -- UI poll (main thread) -------------------------------------------------

    def _poll_ui(self) -> None:
        if self._stop_event.is_set():
            return

        try:
            disp_rgb, result = self._frame_queue.get_nowait()
        except queue.Empty:
            self.after(5, self._poll_ui)
            return

        # Rolling FPS
        now = time.perf_counter()
        self._fps_times.append(now)
        fps = (
            int((len(self._fps_times) - 1) / (self._fps_times[-1] - self._fps_times[0]))
            if len(self._fps_times) >= 2 else 0
        )

        if not self._paused and self._engine:
            state = self._engine.process(
                result,
                self._smooth_steering,
                self._smooth_throttle,
                self._smooth_brake,
            )
            self._smooth_steering = state["steering"]
            self._smooth_throttle = state["throttle"]
            self._smooth_brake    = state["brake"]

            if self._gp_state:
                self._gp_state.update(state)

            self._update_ui(state, fps)

        # Blit frame onto canvas, reusing the same image item
        img   = Image.fromarray(disp_rgb)
        photo = ImageTk.PhotoImage(image=img)
        if self._canvas_image_id is None:
            self._canvas_image_id = self._cam_canvas.create_image(0, 0, anchor="nw", image=photo)
        else:
            self._cam_canvas.itemconfig(self._canvas_image_id, image=photo)
        self._cam_canvas._photo = photo  # keep a reference so GC doesn't collect it

        self.after(16, self._poll_ui)

    def _update_ui(self, state: dict, fps: int) -> None:
        c = self._theme.colors

        # Hand detection dots
        (self._dot_left.set_ok   if state["left_detected"]  else self._dot_left.set_idle)()
        (self._dot_right.set_ok  if state["right_detected"] else self._dot_right.set_idle)()

        # FPS — only update the label when the value changes
        if fps != self._last_fps:
            self._fps_lbl.config(text=f"{fps} fps")
            self._last_fps = fps

        # Telemetry bars (canvas-based, always redraw)
        self._bar_steer.set_value(state["steering"])
        self._bar_throt.set_value(state["throttle"])
        self._bar_brake.set_value(state["brake"])

        # Confidence — only update when the integer % changes
        conf_int = int(state["confidence"] * 100)
        if conf_int != self._last_conf:
            self._conf_lbl.config(text=f"{conf_int}%")
            self._last_conf = conf_int

        # Gesture badges — only redraw on state change
        for key, (lbl, active_color) in self._badges.items():
            val = bool(state.get(key, False))
            if val != self._badge_state[key]:
                lbl.config(
                    bg=active_color        if val else c["border"],
                    fg=c["text_on_accent"] if val else c["text_muted"],
                )
                self._badge_state[key] = val

    # -- controls --------------------------------------------------------------

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._pause_btn.configure_text(">> Resume")
            if self._gp_state:
                self._gp_state.reset()
        else:
            self._pause_btn.configure_text("|| Pause")

    def _do_exit(self) -> None:
        self._stop_event.set()
        if self._gp_state:
            self._gp_state.reset()
        if self._cap:
            self._cap.release()
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass
        self._on_exit()
