"""
GestureDrive — Application Controller
Root window and screen router. All screen transitions are managed here.
"""

import tkinter as tk
from tkinter import messagebox

from .config.paths import CALIB_FILE
from .settings.manager import SettingsManager


class GestureApp:
    """Top-level application object. Creates the root window and owns the screen stack."""

    WIN_W = 1280
    WIN_H = 780

    def __init__(self) -> None:
        self._settings = SettingsManager()

        # Root window must exist before anything touches tkinter or font queries
        self._root = tk.Tk()
        self._root.title("GestureDrive")
        self._root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self._root.minsize(1200, 700)
        self._root.state("zoomed")
        self._root.resizable(True, True)

        # Theme is constructed after root (font queries need a live Tk instance)
        from .ui.theme import Theme
        self._theme = Theme().scale(self._settings.get("ui_scale", 1.0))
        self._root.configure(bg=self._theme.colors["bg_root"])

        self._try_set_icon()

        self._current_frame: tk.Frame = None
        self._show_welcome()

    # -- helpers ---------------------------------------------------------------

    def _try_set_icon(self) -> None:
        try:
            from .config.paths import ASSETS_DIR
            ico = ASSETS_DIR / "icons" / "icon.png"
            if ico.exists():
                img = tk.PhotoImage(file=str(ico))
                self._root.iconphoto(True, img)
        except Exception:
            pass

    def _swap(self, frame: tk.Frame) -> None:
        """Destroy the current screen and display *frame* in its place."""
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

    # -- screen router ---------------------------------------------------------

    def _show_welcome(self) -> None:
        from .ui.welcome import WelcomeScreen
        self._swap(WelcomeScreen(
            self._root,
            theme=self._theme,
            on_calibrate=self._show_calibration,
            on_settings=self._show_settings,
            on_quick_start=self._quick_start,
        ))

    def _show_calibration(self) -> None:
        from .calibration.wizard import CalibrationWizard
        self._swap(CalibrationWizard(
            self._root,
            theme=self._theme,
            settings=self._settings,
            camera_index=self._settings.camera_index,
            on_complete=self._on_calib_done,
            on_cancel=self._show_welcome,
        ))

    def _on_calib_done(self, calib: dict) -> None:
        messagebox.showinfo(
            "Calibration Complete",
            "Your hand positions have been recorded.\n"
            "GestureDrive will now start.",
        )
        self._show_runtime()

    def _quick_start(self) -> None:
        if not CALIB_FILE.exists():
            if messagebox.askyesno(
                "No Calibration Found",
                "No calibration data was found.\n"
                "Would you like to calibrate now?\n\n"
                "(Selecting No uses default values.)",
            ):
                self._show_calibration()
                return
        self._show_runtime()

    def _show_runtime(self) -> None:
        from .ui.runtime import RuntimeScreen
        self._swap(RuntimeScreen(
            self._root,
            theme=self._theme,
            settings=self._settings,
            on_recalibrate=self._show_calibration,
            on_exit=self._show_welcome,
        ))

    def _show_settings(self) -> None:
        from .ui.settings_screen import SettingsScreen
        self._swap(SettingsScreen(
            self._root,
            theme=self._theme,
            settings=self._settings,
            on_back=self._show_welcome,
        ))

    # -- entry point -----------------------------------------------------------

    def run(self) -> None:
        self._root.mainloop()
