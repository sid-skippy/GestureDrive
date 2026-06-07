import json
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional

import cv2
import mediapipe as mp
from PIL import Image, ImageTk

from ..config.paths import CALIB_FILE, MODEL_FILE, SETUP_IMAGES_DIR
from ..ui.theme import Theme
from ..ui.widgets import GDButton, GDCard, SectionHeader


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

CALIBRATION_TIME = 10.0   # seconds to hold each position

STEPS = [
    dict(title="Neutral Steering", hand="left",  icon="✊", collect=False,
         instruction="Make a fist with your LEFT hand and hold it straight forward."),
    dict(title="Steer Left",       hand="left",  icon="↙", collect=False,
         instruction="Rotate/tilt your LEFT fist to the LEFT."),
    dict(title="Steer Right",      hand="left",  icon="↘", collect=False,
         instruction="Rotate/tilt your LEFT fist to the RIGHT."),
    dict(title="Handbrake",        hand="left",  icon="🖐", collect=False,
         instruction="Open your LEFT hand to activate the handbrake."),
    dict(title="Full Throttle",    hand="right", icon="🚀", collect=True, key="full_throttle",
         instruction="Raise your RIGHT thumb as high as comfortable."),
    dict(title="Brake Position",   hand="right", icon="🛑", collect=True, key="brake",
         instruction="Relax your RIGHT thumb beside your middle finger."),
    dict(title="Gear Up",          hand="right", icon="☝", collect=False,
         instruction="Extend only your RIGHT index finger."),
    dict(title="Gear Down",        hand="right", icon="🤙", collect=False,
         instruction="Extend only your RIGHT little finger."),
]

# Maps step index → reference image filename
STEP_IMAGES = {i: f"{i + 1}.jpg" for i in range(len(STEPS))}

HAND_CONNECTIONS = [
    (0, 1),  (1, 2),  (2, 3),  (3, 4),
    (0, 5),  (5, 6),  (6, 7),  (7, 8),
    (5, 9),  (9, 10), (10, 11),(11, 12),
    (9, 13), (13, 14),(14, 15),(15, 16),
    (13, 17),(17, 18),(18, 19),(19, 20),
    (0, 17),
]

_CAM_W, _CAM_H   = 480, 360   # canvas display size
_POLL_INTERVAL_MS = 33         # ~30 FPS


# ---------------------------------------------------------------------------
# CalibrationWizard
# ---------------------------------------------------------------------------

class CalibrationWizard(tk.Frame):
    """
    Step-by-step calibration wizard.
    Guides the user through each gesture, collects landmark samples for
    the data-driven steps, then writes a calibration file and calls *on_complete*.
    """

    def __init__(
        self,
        parent,
        theme: Theme,
        settings,
        camera_index: int,
        on_complete,
        on_cancel,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_root"])

        self._theme       = theme
        self._settings    = settings
        self._cam_idx     = camera_index
        self._on_complete = on_complete
        self._on_cancel   = on_cancel

        self._step      = 0
        self._collected: dict             = {}
        self._samples:   list             = []
        self._start_t:   Optional[float]  = None
        self._running    = True

        self._latest_result = None
        self._result_lock   = threading.Lock()
        self._timestamp     = 0

        self._cap:        Optional[cv2.VideoCapture] = None
        self._landmarker  = None

        self._build()
        self._init_camera()

    # -- layout ----------------------------------------------------------------

    def _build(self) -> None:
        t = self._theme
        c = t.colors

        SectionHeader(self, "SETUP AND CALIBRATION", t).pack(fill="x")

        # Progress dots
        dots_frame = tk.Frame(self, bg=c["bg_root"])
        dots_frame.pack(fill="x", padx=40, pady=12)
        self._dot_labels = []
        for _ in range(len(STEPS)):
            lbl = tk.Label(dots_frame, text="●",
                           font=(t._base_family, 18),
                           bg=c["bg_root"], fg=c["border"])
            lbl.pack(side="left", padx=6)
            self._dot_labels.append(lbl)

        # Two-column body: camera left, instructions right
        body = tk.Frame(self, bg=c["bg_root"])
        body.pack(fill="both", expand=True, padx=20)

        self._build_camera_pane(body, t, c)
        self._build_instruction_pane(body, t, c)

        # Footer
        footer = tk.Frame(self, bg=c["bg_card_deep"])
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text=(
                "Setup progress saves automatically  ·  "
                "You can recalibrate anytime from the runtime screen  ·  Skippy"
            ),
            font=t.font_small,
            bg=c["bg_card_deep"], fg=c["text_muted"],
            pady=5,
        ).pack()

        self._refresh_step_ui()
        self._canvas_image = self._cam_canvas.create_image(0, 0, anchor="nw")

    def _build_camera_pane(self, body, t, c) -> None:
        cam_frame = GDCard(body, t)
        cam_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._cam_canvas = tk.Canvas(
            cam_frame, width=_CAM_W, height=_CAM_H,
            bg="#111111", highlightthickness=0,
        )
        self._cam_canvas.pack(padx=10, pady=10)

        self._cam_status = tk.Label(
            cam_frame, text="Initialising camera…",
            font=t.font_small, bg=c["bg_card"], fg=c["text_muted"],
        )
        self._cam_status.pack(pady=(0, 8))

    def _build_instruction_pane(self, body, t, c) -> None:
        info = GDCard(body, t)
        info.pack(side="left", fill="y", ipadx=16, ipady=16, expand=False)
        info.config(width=320)

        self._icon_lbl = tk.Label(info, text="🖐", font=(t._base_family, 48), bg=c["bg_card"])
        self._icon_lbl.pack(pady=(24, 8))

        self._image_lbl = tk.Label(info, bg=c["bg_card"])
        self._image_lbl.pack(pady=(0, 12))

        self._pov_lbl = tk.Label(info, text="Camera View",
                                  font=t.font_small,
                                  bg=c["bg_card"], fg=c["text_muted"])
        self._pov_lbl.pack(pady=(0, 8))

        self._step_counter = tk.Label(info, text=f"STEP 1 OF {len(STEPS)}",
                                       font=t.font_value,
                                       bg=c["bg_card"], fg=c["accent"])
        self._step_counter.pack()

        self._step_title = tk.Label(info, text="",
                                     font=t.font_title,
                                     bg=c["bg_card"], fg=c["text_primary"],
                                     wraplength=280, justify="center")
        self._step_title.pack(pady=(8, 4))

        self._instr_lbl = tk.Label(info, text="",
                                    font=t.font_body,
                                    bg=c["bg_card"], fg=c["text_secondary"],
                                    wraplength=280, justify="center")
        self._instr_lbl.pack(padx=16)

        # Countdown ring
        self._cd_canvas = tk.Canvas(info, width=100, height=100,
                                     bg=c["bg_card"], highlightthickness=0)
        self._cd_canvas.pack(pady=20)
        self._draw_countdown(CALIBRATION_TIME)

        self._hand_status = tk.Label(info, text="Waiting for hand…",
                                      font=t.font_small,
                                      bg=c["bg_card"], fg=c["warn"])
        self._hand_status.pack()

        btn_row = tk.Frame(info, bg=c["bg_card"])
        btn_row.pack(fill="x", padx=16, pady=16)
        GDButton(btn_row, "Cancel", command=self._cancel,
                 style="ghost", theme=t).pack(side="right", padx=(4, 0))

    # -- camera init -----------------------------------------------------------

    def _init_camera(self) -> None:
        try:
            self._cap = cv2.VideoCapture(self._cam_idx)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_FPS,          60)

            if not self._cap.isOpened():
                raise RuntimeError("Camera not found")
            if not MODEL_FILE.exists():
                raise RuntimeError(f"MediaPipe model not found:\n{MODEL_FILE}")

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
            self._cam_status.config(text="Camera ready", fg=self._theme.colors["ok"])
            self._poll_camera()

        except Exception as exc:
            self._cam_status.config(text=f"Error: {exc}", fg=self._theme.colors["error"])
            messagebox.showerror("Camera Error", f"Could not initialise camera:\n{exc}")

    # -- camera / calibration poll (main thread via after()) -------------------

    def _poll_camera(self) -> None:
        if not self._running or self._cap is None:
            return

        ret, frame = self._cap.read()
        if not ret:
            self._cam_status.config(text="Camera signal lost. Waiting…",
                                     fg=self._theme.colors["warn"])
            self.after(_POLL_INTERVAL_MS, self._poll_camera)
            return

        if self._cam_status.cget("text") != "Camera ready":
            self._cam_status.config(text="Camera ready", fg=self._theme.colors["ok"])

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]

        # MediaPipe detection
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._timestamp += 1
        try:
            self._landmarker.detect_async(mp_image, self._timestamp)
        except Exception:
            pass

        with self._result_lock:
            result = self._latest_result

        # Draw skeleton overlay
        hand_found = False
        if result and result.hand_landmarks:
            hand_found = True
            for i, lm in enumerate(result.hand_landmarks):
                raw   = result.handedness[i][0].display_name
                color = (60, 200, 100) if raw == "Right" else (70, 130, 220)
                pts   = [(int(p.x * w), int(p.y * h)) for p in lm]
                for a, b in HAND_CONNECTIONS:
                    cv2.line(frame, pts[a], pts[b], color, 2)
                for pt in pts:
                    cv2.circle(frame, pt, 4, color, -1)

        # Calibration sample collection
        step_info = STEPS[self._step]
        hand_side = step_info["hand"]
        key       = step_info.get("key")
        target_lm = self._get_hand(result, hand_side)

        if target_lm:
            hand_found = True
            if self._start_t is None:
                self._start_t = time.time()
            elapsed   = time.time() - self._start_t
            countdown = max(0.0, CALIBRATION_TIME - elapsed)

            if step_info["collect"]:
                if key == "full_throttle":
                    self._samples.append(target_lm[2].y - target_lm[4].y)
                elif key == "brake":
                    self._samples.append(target_lm[4].y - target_lm[8].y)

            self._draw_countdown(countdown)

            if elapsed >= CALIBRATION_TIME:
                if step_info["collect"]:
                    self._collected[key] = (
                        sum(self._samples) / len(self._samples) if self._samples else 0.0
                    )
                self._advance_step()
                self.after(_POLL_INTERVAL_MS, self._poll_camera)
                return
        else:
            self._start_t = None
            self._draw_countdown(CALIBRATION_TIME)

        # Hand status label
        side_label = hand_side.upper()
        if hand_found and target_lm:
            self._hand_status.config(text="✓ Hand detected — hold steady",
                                      fg=self._theme.colors["ok"])
        else:
            self._hand_status.config(text=f"Show your {side_label} hand to the camera",
                                      fg=self._theme.colors["warn"])

        # Blit frame to canvas
        disp  = cv2.resize(frame, (_CAM_W, _CAM_H))
        img   = Image.fromarray(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(image=img)
        self._cam_canvas.itemconfig(self._canvas_image, image=photo)
        self._cam_canvas._photo = photo  # keep reference so GC doesn't collect it

        self.after(_POLL_INTERVAL_MS, self._poll_camera)

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _get_hand(result, side: str):
        """
        Return the landmark list for *side* (``"left"`` or ``"right"`` from
        the user's perspective), or ``None`` if that hand isn't detected.
        MediaPipe labels are mirrored, so we invert them here.
        """
        if not result:
            return None
        mp_label = "Right" if side == "left" else "Left"
        for i, lm in enumerate(result.hand_landmarks):
            if result.handedness[i][0].display_name == mp_label:
                return lm
        return None

    def _draw_countdown(self, seconds: float) -> None:
        c  = self._theme.colors
        cx, cy, r = 50, 50, 38
        self._cd_canvas.delete("all")

        # Background ring
        self._cd_canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                     outline=c["border"], width=4)
        # Progress arc
        if seconds < CALIBRATION_TIME:
            angle = int(360 * (1.0 - seconds / CALIBRATION_TIME))
            self._cd_canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=90, extent=-angle,
                outline=c["ok"], width=4, style="arc",
            )
        # Number / tick
        text = str(max(0, int(seconds + 0.999))) if seconds > 0 else "✓"
        self._cd_canvas.create_text(
            cx, cy, text=text,
            font=self._theme.font_value,
            fill=c["ok"] if seconds < 1 else c["text_primary"],
        )

    def _refresh_step_ui(self) -> None:
        t = self._theme
        c = t.colors
        s = STEPS[self._step]

        self._step_counter.config(text=f"STEP {self._step + 1} OF {len(STEPS)}")
        self._step_title.config(text=s["title"])
        self._instr_lbl.config(text=s["instruction"])
        self._icon_lbl.config(text=s["icon"])

        img_path = SETUP_IMAGES_DIR / STEP_IMAGES[self._step]
        if img_path.exists():
            img = Image.open(img_path)
            img.thumbnail((250, 180))
            self._step_img = ImageTk.PhotoImage(img)
            self._image_lbl.config(image=self._step_img)
        else:
            self._image_lbl.config(image="")

        for i, dot in enumerate(self._dot_labels):
            dot.config(fg=c["ok"] if i < self._step else c["accent"] if i == self._step else c["border"])

    # -- flow control ----------------------------------------------------------

    def _advance_step(self) -> None:
        self._samples = []
        self._start_t = None
        if self._step < len(STEPS) - 1:
            self._step += 1
            self._refresh_step_ui()
        else:
            self._finish()

    def _finish(self) -> None:
        self._running = False
        calib = self._compute_calibration()
        self._save_calibration(calib)
        self._cleanup()
        self._on_complete(calib)

    def _cancel(self) -> None:
        self._running = False
        self._cleanup()
        self._on_cancel()

    def _cleanup(self) -> None:
        if self._cap:
            self._cap.release()
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass

    # -- calibration computation -----------------------------------------------

    def _compute_calibration(self) -> dict:
        full_throttle  = self._collected.get("full_throttle", 0.10)
        brake_position = self._collected.get("brake",         0.08)
        return {
            "THUMB_Y_SCALE":   max(0.05, full_throttle),
            "BRAKE_THRESHOLD": max(0.05, brake_position),
        }

    @staticmethod
    def _save_calibration(calib: dict) -> None:
        CALIB_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALIB_FILE, "w") as f:
            json.dump(calib, f, indent=2)
