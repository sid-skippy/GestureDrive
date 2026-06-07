import webbrowser
import tkinter as tk

from ..utils.driver_check import is_vigem_installed
from .scrollable_frame import ScrollableFrame
from .theme import Theme
from .widgets import GDButton


class WelcomeScreen(tk.Frame):
    """Landing screen with quick-guide cards, driver status and action buttons."""

    _GUIDE_CARDS = [
        (
            "HOW IT WORKS",
            "- LEFT HAND\n"
            "  • Tilt fist to steer\n"
            "  • Open hand for handbrake\n\n"
            "- RIGHT HAND\n"
            "  • Thumb for throttle\n"
            "  • Index finger — Gear Up\n"
            "  • Little finger — Gear Down\n"
            "  • Lower thumb to brake",
        ),
        (
            "CAMERA",
            "- Resolution\n"
            "  640 x 480 or higher\n\n"
            "- Frame rate\n"
            "  Capped 30 FPS recommended\n\n"
            "- Keep your webcam straight\n"
            "  and not at an angle",
        ),
        (
            "LIGHTING",
            "✓ Bright room\n"
            "✓ Plain background\n"
            "✓ Even lighting\n\n"
            "✗ Direct glare\n"
            "✗ Strong backlight",
        ),
    ]

    _VIGEM_URL = "https://github.com/nefarius/ViGEmBus/releases"

    def __init__(
        self,
        parent,
        theme: Theme,
        on_calibrate,
        on_settings,
        on_quick_start,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_root"])

        self._theme            = theme
        self._on_calibrate     = on_calibrate
        self._on_settings      = on_settings
        self._on_quick         = on_quick_start
        self._vigem_installed  = is_vigem_installed()

        self._build()

    # -- layout ----------------------------------------------------------------

    def _build(self) -> None:
        t = self._theme
        c = t.colors

        # Top racing stripe
        tk.Frame(self, bg=c["accent"], height=5).pack(fill="x")

        # Two-column body: dark hero panel on the left, scrollable content on the right
        body = tk.Frame(self, bg=c["bg_root"])
        body.pack(fill="both", expand=True)

        hero = tk.Frame(body, bg=c["hero_bg"], width=620)
        hero.pack(side="left", fill="y")
        hero.pack_propagate(False)
        self._build_hero(hero)

        right_container = tk.Frame(body, bg=c["bg_root"])
        right_container.pack(side="left", fill="both", expand=True)

        scroll = ScrollableFrame(right_container, bg=c["bg_root"])
        scroll.pack(fill="both", expand=True, pady=(0, 20))

        self._build_content(scroll.content)

        actions_frame = tk.Frame(right_container, bg=c["bg_root"])
        actions_frame.pack(fill="x", side="bottom", padx=40, pady=20)
        self._build_actions(actions_frame)

        # Footer strip
        footer = tk.Frame(self, bg=c["hero_bg"])
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer,
            text="GestureDrive  v1.0   ·   Powered by MediaPipe and vgamepad   ·   Skippy",
            font=t.font_small,
            bg=c["hero_bg"], fg=c["hero_subtext"],
            pady=5,
        ).pack()

    def _build_hero(self, parent) -> None:
        t = self._theme
        c = t.colors

        wrap = tk.Frame(parent, bg=c["hero_bg"])
        wrap.place(relx=0.08, rely=0.5, anchor="w")

        tk.Label(wrap, text="[ GESTURE-BASED RACING CONTROL ]",
                 font=(t._base_family, 8, "normal"),
                 bg=c["hero_bg"], fg="#000000").pack(anchor="w", pady=(0, 12))

        tk.Label(wrap, text="Gesture\nDrive",
                 font=(t._bold_family, 64, "normal"),
                 bg=c["hero_bg"], fg="#000000",
                 justify="left").pack(anchor="w")

        tk.Frame(wrap, bg="#000000", height=3, width=80).pack(anchor="w", pady=(12, 16))

        tk.Label(wrap,
                 text="Real-time hand tracking with gesture steering,\nthrottle, handbrake and gear control.",
                 font=t.font_subtitle,
                 bg=c["hero_bg"], fg="#000000",
                 justify="left").pack(anchor="w")

        badge = tk.Frame(wrap, bg=c["accent"])
        badge.pack(anchor="w", pady=(24, 0))
        tk.Label(badge, text=" v1.0 RELEASE ",
                 font=(t._bold_family, 9, "normal"),
                 bg="#000000", fg="#FFFFFF",
                 padx=6, pady=3).pack()

    def _build_content(self, parent) -> None:
        t = self._theme
        c = t.colors

        content = tk.Frame(parent, bg=c["bg_root"])
        content.pack(fill="both", expand=True, padx=40, pady=36)

        tk.Label(content, text="QUICK GUIDE",
                 font=(t._bold_family, 10, "normal"),
                 bg=c["bg_root"], fg=c["accent"]).pack(anchor="w", pady=(0, 12))

        # Three info cards
        cards_frame = tk.Frame(content, bg=c["bg_root"])
        cards_frame.pack(fill="x", pady=(0, 28))
        cards_frame.columnconfigure((0, 1, 2), weight=1, uniform="cards")

        for col, (title, body) in enumerate(self._GUIDE_CARDS):
            self._build_info_card(cards_frame, title, body, col)

        tk.Frame(content, bg=c["border"], height=1).pack(fill="x", pady=(0, 24))

        self._build_driver_status(content)

        # Spacer so the action buttons stay outside the scroll area
        tk.Frame(content, bg=c["bg_root"]).pack(fill="both", expand=True)

    def _build_driver_status(self, parent) -> None:
        t = self._theme
        c = t.colors

        status = tk.Frame(parent,
                          bg=c["bg_card"],
                          highlightthickness=1,
                          highlightbackground=c["border"])
        status.pack(fill="x", pady=(0, 24))

        if self._vigem_installed:
            tk.Label(status, text="✓  ViGEm Bus Driver Detected",
                     font=(t._bold_family, 11),
                     bg=c["bg_card"], fg="#2E7D32").pack(anchor="w", padx=15, pady=(12, 4))
            tk.Label(status,
                     text="GestureDrive is ready to create a virtual Xbox controller.",
                     bg=c["bg_card"], fg=c["text_secondary"]).pack(anchor="w", padx=15, pady=(0, 12))
        else:
            tk.Label(status, text="⚠  ViGEm Bus Driver Not Detected",
                     font=(t._bold_family, 11),
                     bg=c["bg_card"], fg=c["error"]).pack(anchor="w", padx=15, pady=(12, 4))
            tk.Label(
                status,
                text=(
                    "GestureDrive requires the ViGEm Bus Driver to emulate an Xbox controller.\n"
                    "You may need to restart your PC after installing."
                ),
                justify="left",
                bg=c["bg_card"], fg=c["text_secondary"],
            ).pack(anchor="w", padx=15, pady=(0, 12))
            GDButton(
                status, "Install Driver from GitHub",
                command=lambda: webbrowser.open(self._VIGEM_URL),
                style="primary", theme=t,
            ).pack(anchor="w", padx=15, pady=(0, 15))

    def _build_actions(self, parent) -> None:
        t = self._theme
        c = t.colors

        tk.Label(parent, text="GET STARTED",
                 font=(t._bold_family, 10, "normal"),
                 bg=c["bg_root"], fg=c["accent"]).pack(anchor="w", pady=(0, 12))

        btn_row = tk.Frame(parent, bg=c["bg_root"])
        btn_row.pack(fill="x")
        btn_row.columnconfigure((0, 1, 2), weight=1, uniform="btns")

        start_btn = GDButton(btn_row, "TUTORIAL AND CALIBRATION",
                             command=self._on_calibrate, style="primary", theme=t)
        start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        quick_btn = GDButton(btn_row, "QUICK START",
                             command=self._on_quick, style="secondary", theme=t)
        quick_btn.grid(row=0, column=1, sticky="ew", padx=4)

        GDButton(btn_row, "SETTINGS",
                 command=self._on_settings, style="secondary", theme=t).grid(
            row=0, column=2, sticky="ew", padx=(8, 0)
        )

        if not self._vigem_installed:
            start_btn.disable()
            quick_btn.disable()

    # -- helpers ---------------------------------------------------------------

    def _build_info_card(self, parent, title: str, body: str, col: int) -> None:
        t = self._theme
        c = t.colors

        pad_left  = 0  if col == 0 else 10
        pad_right = 10 if col < 2  else 0

        card = tk.Frame(parent,
                        bg=c["bg_card"],
                        highlightthickness=1,
                        highlightbackground=c["border"])
        card.grid(row=0, column=col, sticky="nsew",
                  padx=(pad_left, pad_right), pady=4)

        tk.Frame(card, bg=c["accent"], height=3).pack(fill="x")

        tk.Label(card, text=title,
                 font=(t._bold_family, 10, "normal"),
                 bg=c["bg_card"], fg=c["text_primary"]).pack(anchor="w", padx=18, pady=(16, 8))

        tk.Frame(card, bg=c["border"], height=1).pack(fill="x", padx=18, pady=(0, 8))

        tk.Label(card, text=body,
                 font=t.font_small,
                 bg=c["bg_card"], fg=c["text_secondary"],
                 justify="left", anchor="nw",
                 wraplength=260).pack(anchor="w", fill="both", expand=True, padx=18, pady=(4, 18))
