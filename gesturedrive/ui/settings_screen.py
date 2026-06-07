import tkinter as tk
from tkinter import messagebox

from .scrollable_frame import ScrollableFrame
from .theme import Theme
from .widgets import GDButton, GDSlider


class SettingsScreen(tk.Frame):
    """Settings panel with sliders and control-binding selectors."""

    BUTTON_CHOICES = ["None", "A", "B", "X", "Y", "LB", "RB"]

    # Slider definitions: (section_title, [slider_kwargs, ...], grid_column)
    _SLIDER_SECTIONS = [
        (
            "STEERING",
            [
                dict(label="Sensitivity", key="steering_sensitivity", from_=0.3,  to=3.0,  resolution=0.05),
                dict(label="Dead Zone",   key="dead_zone",            from_=0.0,  to=0.5,  resolution=0.01),
                dict(label="Smoothing",   key="smoothing",            from_=0.05, to=0.95, resolution=0.01),
            ],
            0,
        ),
        (
            "THROTTLE, BRAKE AND GEARS",
            [
                dict(label="Sensitivity",             key="throttle_sensitivity", from_=0.3,  to=3.0,  resolution=0.05),
                dict(label="Little Finger Threshold", key="pinky_threshold",      from_=0.05, to=0.30, resolution=0.005),
                dict(label="Index Finger Threshold",  key="index_threshold",      from_=0.05, to=0.30, resolution=0.005),
            ],
            1,
        ),
    ]

    # Control-binding definitions: (display_label, settings_key)
    _BINDINGS = [
        ("Handbrake Gesture — Left little finger",  "handbrake_button"),
        ("Gear Up Gesture — Right index finger",    "gear_up_button"),
        ("Gear Down Gesture — Right little finger", "gear_down_button"),
    ]

    def __init__(self, parent, theme: Theme, settings, on_back) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_root"])

        self._theme    = theme
        self._settings = settings
        self._on_back  = on_back

        self._build()

    # -- layout ----------------------------------------------------------------

    def _build(self) -> None:
        t = self._theme
        c = t.colors

        # Racing stripes
        tk.Frame(self, bg=c["accent"],   height=5).pack(fill="x")
        tk.Frame(self, bg=c["bg_strip"], height=2).pack(fill="x")

        # Header bar
        header_inner = tk.Frame(tk.Frame(self, bg=c["hero_bg"]).pack(fill="x") or self, bg=c["hero_bg"])
        # Rebuild properly so we can pack children into the inner frame
        self._build_header()

        # Scrollable two-column body
        content_area = tk.Frame(self, bg=c["bg_root"])
        content_area.pack(fill="both", expand=True)

        scroll = ScrollableFrame(content_area, bg=c["bg_root"])
        scroll.pack(fill="both", expand=True, padx=32, pady=24)

        body = scroll.content
        body.configure(bg=c["bg_root"])
        body.columnconfigure(0, weight=1, uniform="cols")
        body.columnconfigure(1, weight=1, uniform="cols")

        for row_idx, (title, sliders, col) in enumerate(self._SLIDER_SECTIONS):
            self._build_slider_section(body, title, sliders, row=row_idx // 2, col=col)

        self._build_controls_section(body, row=1)

        # Bottom bar
        bot_frame = tk.Frame(self, bg=c["bg_card_deep"])
        bot_frame.pack(fill="x", side="bottom")
        bot_inner = tk.Frame(bot_frame, bg=c["bg_card_deep"])
        bot_inner.pack(fill="x", padx=24, pady=10)

        GDButton(bot_inner, "BACK",
                 command=self._save_and_back, style="primary", theme=t).pack(side="right")
        GDButton(bot_inner, "RESET TO DEFAULTS",
                 command=self._reset_defaults, style="secondary", theme=t).pack(side="right", padx=(0, 12))
        tk.Label(bot_inner, text="Changes are saved automatically",
                 font=t.font_small, bg=c["bg_card_deep"], fg=c["text_muted"]).pack(side="left")

    def _build_header(self) -> None:
        t = self._theme
        c = t.colors

        header = tk.Frame(self, bg=c["hero_bg"])
        header.pack(fill="x")
        inner = tk.Frame(header, bg=c["hero_bg"])
        inner.pack(fill="x", padx=32, pady=14)

        tk.Label(inner, text="SETTINGS",
                 font=(t._bold_family, 22, "normal"),
                 bg=c["hero_bg"], fg="#FFFFFF").pack(side="left")
        tk.Label(inner, text="Tune your controls",
                 font=t.font_small,
                 bg=c["hero_bg"], fg=c["hero_subtext"]).pack(side="left", padx=(16, 0), pady=(6, 0))

    # -- slider section --------------------------------------------------------

    def _build_slider_section(self, parent, title: str, items: list, row: int, col: int) -> None:
        t = self._theme
        c = t.colors

        pad = (0, 12) if col == 0 else (12, 0)
        card = self._card(parent)
        card.grid(row=row, column=col, sticky="nsew", padx=pad, pady=(0, 16))

        tk.Frame(card, bg=c["accent"], height=3).pack(fill="x")
        tk.Label(card, text=title,
                 font=(t._bold_family, 12, "normal"),
                 bg=c["bg_card"], fg=c["text_primary"],
                 padx=16, pady=12).pack(anchor="w")
        tk.Frame(card, bg=c["border"], height=1).pack(fill="x")

        for kwargs in items:
            GDSlider(card, theme=t, settings=self._settings, **kwargs).pack(fill="x", padx=16, pady=8)

    # -- control bindings section ----------------------------------------------

    def _build_controls_section(self, parent, row: int) -> None:
        t = self._theme
        c = t.colors

        card = self._card(parent)
        card.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(0, 16))

        tk.Frame(card, bg=c["accent"], height=3).pack(fill="x")
        tk.Label(card, text="CONTROL BINDINGS",
                 font=(t._bold_family, 12, "normal"),
                 bg=c["bg_card"], fg=c["text_primary"],
                 padx=16, pady=12).pack(anchor="w")
        tk.Frame(card, bg=c["border"], height=1).pack(fill="x")

        tk.Label(
            card,
            text=(
                "The default layout is optimised for the Forza Horizon series, "
                "The Crew series, and the Need for Speed series.\n\n"
                "Driving controls use the built-in GestureDrive hand gestures —\n"
                "  • Tilt left fist to steer\n"
                "  • Open left hand fist for handbrake\n"
                "  • Raise right thumb for throttle\n"
                "  • Flick right index finger for gear up\n"
                "  • Flick right little finger for gear down\n\n"
                "Steering, throttle and brake controls remain fixed. "
                "You can still change them in your game settings."
            ),
            font=t.font_small,
            justify="left",
            wraplength=900,
            bg=c["bg_card"],
            fg=c["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(12, 12))

        for label, key in self._BINDINGS:
            self._build_binding_selector(card, label, key)

    def _build_binding_selector(self, parent, label: str, setting_key: str) -> None:
        t = self._theme
        c = t.colors

        row = tk.Frame(parent, bg=c["bg_card"])
        row.pack(fill="x", padx=16, pady=8)

        tk.Label(row, text=label,
                 font=t.font_body,
                 bg=c["bg_card"], fg=c["text_primary"]).pack(side="left")

        selector = tk.Frame(row, bg=c["bg_card"])
        selector.pack(side="right")

        value_lbl = tk.Label(
            selector,
            text=self._settings.get(setting_key),
            font=(t._bold_family, 11),
            bg=c["accent_subtle"], fg=c["accent"],
            width=6, pady=6,
        )

        def _make_arrow(text: str) -> tk.Label:
            return tk.Label(
                selector, text=text,
                font=(t._bold_family, 12),
                bg=c["bg_card"], fg=c["accent"],
                cursor="hand2", padx=8,
            )

        left_btn  = _make_arrow("◀")
        right_btn = _make_arrow("▶")

        left_btn.pack(side="left")
        value_lbl.pack(side="left", padx=4)
        right_btn.pack(side="left")

        def _change(direction: int) -> None:
            current = self._settings.get(setting_key)
            idx     = self.BUTTON_CHOICES.index(current)
            in_use  = {
                self._settings.get("handbrake_button"),
                self._settings.get("gear_up_button"),
                self._settings.get("gear_down_button"),
            } - {current}

            for step in range(1, len(self.BUTTON_CHOICES) + 1):
                candidate = self.BUTTON_CHOICES[(idx + direction * step) % len(self.BUTTON_CHOICES)]
                if candidate == "None" or candidate not in in_use:
                    break

            self._settings.set(setting_key, candidate)
            value_lbl.config(text=candidate)

        left_btn.bind("<Button-1>",  lambda _: _change(-1))
        right_btn.bind("<Button-1>", lambda _: _change(+1))

    # -- helpers ---------------------------------------------------------------

    def _card(self, parent) -> tk.Frame:
        c = self._theme.colors
        return tk.Frame(
            parent,
            bg=c["bg_card"],
            highlightthickness=1,
            highlightbackground=c["border"],
        )

    # -- actions ---------------------------------------------------------------

    def _save_and_back(self) -> None:
        self._settings.save()
        self._on_back()

    def _reset_defaults(self) -> None:
        if not messagebox.askyesno(
            "Reset Settings",
            "Restore all settings to their default values?\n"
            "GestureDrive will restart to apply the changes.",
        ):
            return
        self._settings.reset_defaults()
        self._save_and_back()
