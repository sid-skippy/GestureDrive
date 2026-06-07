import tkinter as tk

from .theme import Theme


# ---------------------------------------------------------------------------
# GDButton
# ---------------------------------------------------------------------------

class GDButton(tk.Frame):
    """
    Accent-coloured button with a hover animation.

    *style* is one of ``"primary"`` | ``"secondary"`` | ``"danger"`` | ``"ghost"``.
    """

    _STYLES = {
        "primary":   ("accent",      "text_on_accent", "accent_hover"),
        "secondary": ("bg_card_deep", "text_primary",   "border"),
        "danger":    ("error",        "text_on_accent", None),
        "ghost":     ("bg_root",      "accent",         "accent_subtle"),
    }
    _DANGER_HOVER = "#9B2220"

    def __init__(
        self,
        parent,
        text: str,
        command=None,
        style: str = "primary",
        theme: Theme = None,
        **kw,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=parent["bg"], **kw)

        bg_key, fg_key, hover_key = self._STYLES.get(style, self._STYLES["primary"])
        self._bg    = c[bg_key]
        self._fg    = c[fg_key]
        self._hover = self._DANGER_HOVER if hover_key is None else c[hover_key]
        self._cmd   = command
        self._enabled = True

        self._btn = tk.Label(
            self,
            text=text,
            font=theme.font_button,
            bg=self._bg,
            fg=self._fg,
            cursor="hand2",
            padx=24,
            pady=10,
        )
        self._btn.pack(fill="x")

        self._btn.bind("<Enter>",    self._on_enter)
        self._btn.bind("<Leave>",    self._on_leave)
        self._btn.bind("<Button-1>", self._on_click)

    # -- event handlers --------------------------------------------------------

    def _on_enter(self, _) -> None:
        if self._enabled:
            self._btn.config(bg=self._hover)

    def _on_leave(self, _) -> None:
        if self._enabled:
            self._btn.config(bg=self._bg)

    def _on_click(self, _) -> None:
        if self._enabled and self._cmd:
            self._cmd()

    # -- public API ------------------------------------------------------------

    def disable(self) -> None:
        self._enabled = False
        self._btn.config(bg="#CFCFCF", fg="#777777", cursor="arrow")

    def enable(self) -> None:
        self._enabled = True
        self._btn.config(bg=self._bg, fg=self._fg, cursor="hand2")

    def configure_text(self, text: str) -> None:
        self._btn.config(text=text)


# ---------------------------------------------------------------------------
# GDModernSlider  (canvas-based drag slider)
# ---------------------------------------------------------------------------

class GDModernSlider(tk.Canvas):
    """A minimal canvas slider that reports values in [0, 1]."""

    _PADDING = 12   # horizontal inset for the track end-caps
    _KNOB_R  = 8    # knob radius in pixels
    _TRACK_W = 8    # track line width

    def __init__(
        self,
        parent,
        width: int = 600,
        height: int = 30,
        value: float = 0.5,
        accent: str = "#C026D3",
        track: str = "#E9D5FF",
        command=None,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            highlightthickness=0,
            bg=parent["bg"],
        )
        self._value   = value
        self._accent  = accent
        self._track   = track
        self._command = command

        self.bind("<Button-1>",   self._on_click)
        self.bind("<B1-Motion>",  self._on_click)
        self.bind("<Configure>",  lambda _: self._draw())
        self._draw()

    # -- drawing ---------------------------------------------------------------

    def _draw(self) -> None:
        self.delete("all")
        p = self._PADDING
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        y = h // 2

        track_x1, track_x2 = p, w - p
        knob_x = track_x1 + self._value * (track_x2 - track_x1)
        r = self._KNOB_R

        # Background track
        self.create_line(track_x1, y, track_x2, y, width=self._TRACK_W, fill=self._track)
        # Filled portion
        self.create_line(track_x1, y, knob_x,   y, width=self._TRACK_W, fill=self._accent)
        # Knob
        self.create_oval(
            knob_x - r, y - r, knob_x + r, y + r,
            fill=self._accent, outline="#000000", width=2,
        )

    # -- interaction -----------------------------------------------------------

    def _on_click(self, event) -> None:
        p = self._PADDING
        w = self.winfo_width()
        self._value = max(0.0, min(1.0, (event.x - p) / (w - 2 * p)))
        self._draw()
        if self._command:
            self._command(self._value)


# ---------------------------------------------------------------------------
# GDSlider  (labeled slider with live value readout)
# ---------------------------------------------------------------------------

class GDSlider(tk.Frame):
    """Labeled slider bound to a settings key, with a live numeric readout."""

    def __init__(
        self,
        parent,
        label: str,
        key: str,
        from_: float,
        to: float,
        resolution: float,
        theme: Theme,
        settings,
        **kw,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_card"], **kw)

        self._key      = key
        self._settings = settings
        self._from     = from_
        self._to       = to

        initial = settings.get(key)

        # Label row
        row = tk.Frame(self, bg=c["bg_card"])
        row.pack(fill="x", padx=2)

        tk.Label(
            row, text=label,
            font=theme.font_label,
            bg=c["bg_card"], fg=c["text_secondary"],
        ).pack(side="left")

        self._val_lbl = tk.Label(
            row, text=f"{initial:.2f}",
            font=theme.font_mono,
            bg=c["bg_card"], fg=c["accent"],
            width=6, anchor="e",
        )
        self._val_lbl.pack(side="right")

        # Slider
        self._slider = GDModernSlider(
            self,
            value=(initial - from_) / (to - from_),
            accent=c["accent"],
            track=c["accent_subtle"],
            command=self._on_change,
        )
        self._slider.pack(fill="x", expand=True, pady=(4, 0))

    def _on_change(self, pct: float) -> None:
        value = round(self._from + pct * (self._to - self._from), 3)
        self._val_lbl.config(text=f"{value:.2f}")
        self._settings.set(self._key, value)


# ---------------------------------------------------------------------------
# GDStatusDot  (coloured indicator with label)
# ---------------------------------------------------------------------------

class GDStatusDot(tk.Frame):
    """Coloured dot indicator with a text label."""

    def __init__(self, parent, label: str, theme: Theme, **kw) -> None:
        c = theme.colors
        super().__init__(parent, bg=parent["bg"], **kw)
        self._c = c

        self._dot = tk.Label(
            self, text="●",
            font=theme.font_body,
            bg=parent["bg"], fg=c["text_muted"],
        )
        self._dot.pack(side="left", padx=(0, 4))

        tk.Label(
            self, text=label,
            font=theme.font_small,
            bg=parent["bg"], fg=c["text_secondary"],
        ).pack(side="left")

    def set_ok(self)    -> None: self._dot.config(fg=self._c["ok"])
    def set_warn(self)  -> None: self._dot.config(fg=self._c["warn"])
    def set_error(self) -> None: self._dot.config(fg=self._c["error"])
    def set_idle(self)  -> None: self._dot.config(fg=self._c["text_muted"])


# ---------------------------------------------------------------------------
# GDBar  (horizontal fill bar for telemetry)
# ---------------------------------------------------------------------------

class GDBar(tk.Frame):
    """
    Horizontal fill bar for steering / throttle / brake telemetry display.

    *mode* is ``"center"`` (steering, bidirectional) or ``"left"`` (throttle / brake).
    """

    def __init__(
        self,
        parent,
        label: str,
        theme: Theme,
        mode: str = "left",
        color: str = None,
        **kw,
    ) -> None:
        c = theme.colors
        super().__init__(parent, bg=parent["bg"], **kw)

        self._mode  = mode
        self._color = color or c["accent"]
        self._c     = c

        tk.Label(
            self, text=label,
            font=theme.font_small,
            bg=parent["bg"], fg=c["text_muted"],
            anchor="w", width=10,
        ).pack(side="left", padx=(0, 6))

        self._track = tk.Canvas(
            self, height=12,
            bg=c["border"], highlightthickness=0,
        )
        self._track.pack(side="left", fill="x", expand=True)

        self._pct_lbl = tk.Label(
            self, text="0%",
            font=theme.font_small,
            bg=parent["bg"], fg=c["text_secondary"],
            width=5,
        )
        self._pct_lbl.pack(side="left", padx=(6, 0))

    def set_value(self, v: float) -> None:
        """
        Update the bar.  *v* is in ``[-1, 1]`` for center mode,
        ``[0, 1]`` for left mode.
        """
        self._track.update_idletasks()
        w = self._track.winfo_width()
        h = self._track.winfo_height()
        if w < 2:
            return

        self._track.delete("all")
        self._track.config(bg=self._c["border"])

        if self._mode == "center":
            mid    = w // 2
            fill_w = int(abs(v) * (w // 2))
            if v < -0.01:
                self._track.create_rectangle(mid - fill_w, 0, mid, h, fill=self._c["warn"],  outline="")
            elif v > 0.01:
                self._track.create_rectangle(mid, 0, mid + fill_w, h, fill=self._color, outline="")
            # Centre tick mark
            self._track.create_rectangle(mid - 1, 0, mid + 1, h, fill=self._c["text_muted"], outline="")
            self._pct_lbl.config(text=f"{int(v * 100):+d}%")
        else:
            fill_w = int(max(0.0, min(1.0, v)) * w)
            self._track.create_rectangle(0, 0, fill_w, h, fill=self._color, outline="")
            self._pct_lbl.config(text=f"{int(v * 100)}%")


# ---------------------------------------------------------------------------
# GDCard  (styled card container)
# ---------------------------------------------------------------------------

class GDCard(tk.Frame):
    """A bordered card container using the ``bg_card`` colour."""

    def __init__(self, parent, theme: Theme, **kw) -> None:
        c = theme.colors
        super().__init__(
            parent,
            bg=c["bg_card"],
            highlightthickness=1,
            highlightbackground=c["border"],
            **kw,
        )


# ---------------------------------------------------------------------------
# SectionHeader  (accent-coloured section divider)
# ---------------------------------------------------------------------------

class SectionHeader(tk.Frame):
    """Accent-coloured strip used as a section divider."""

    def __init__(self, parent, text: str, theme: Theme, **kw) -> None:
        c = theme.colors
        super().__init__(parent, bg=c["bg_strip"], **kw)
        tk.Label(
            self, text=text.upper(),
            font=theme.font_label,
            bg=c["bg_strip"], fg=c["text_on_accent"],
            padx=16, pady=6,
        ).pack(side="left")
