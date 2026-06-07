import ctypes
import tkinter.font as tkfont
from pathlib import Path
from typing import Optional

from ..config.paths import FONTS_DIR


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

PALETTE = {
    # Backgrounds
    "bg_root":      "#F7F8F8",
    "bg_card":      "#FFFFFF",
    "bg_card_deep": "#FDF0F8",
    "bg_input":     "#FFFFFF",
    "bg_strip":     "#38B2A6",

    # Hero section
    "hero_bg":      "#E12A9B",
    "hero_label":   "#FDE7F4",
    "hero_subtext": "#FFF5FB",
    "hero_line":    "#FFFFFF",
    "hero_badge_bg": "#FFFFFF",
    "hero_badge_fg": "#E12A9B",

    # Text
    "text_primary":   "#1B1E22",
    "text_secondary": "#59616B",
    "text_muted":     "#8A939D",
    "text_on_accent": "#FFFFFF",

    # Primary accent
    "accent":        "#38B2A6",
    "accent_hover":  "#2D948A",
    "accent_light":  "#9AE0D8",
    "accent_subtle": "#E6FAF8",

    # Secondary accent
    "accent_alt": "#E12A9B",

    # Status
    "ok":    "#16A34A",
    "warn":  "#F59E0B",
    "error": "#DC2626",

    # Borders
    "border":       "#DCE5E4",
    "border_focus": "#38B2A6",

    # Card states
    "card_hover":    "#F8FBFB",
    "card_selected": "#E6FAF8",

    # Status panels
    "success_bg": "#ECFDF3",
    "success_fg": "#15803D",
    "warning_bg": "#FFF7ED",
    "warning_fg": "#C2410C",
    "error_bg":   "#FEF2F2",
    "error_fg":   "#B91C1C",
}


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

_FONT_REGULAR    = "neuehaasgrottext-55roman-trial.ttf"
_FONT_BOLD       = "neuehaasgrotdispround-65medium-trial.ttf"
_FAMILY_REGULAR  = "HaasGrot Text 55 Rm Trial"
_FAMILY_BOLD     = "HaasGrot Disp R 65 Md Trial"
_FAMILY_FALLBACK = "Segoe UI"


def _load_font_file(path: Path) -> bool:
    """Register a private font with GDI so Tk can use it."""
    result = ctypes.windll.gdi32.AddFontResourceExW(str(path), 0x10, 0)
    return result > 0


def load_custom_fonts() -> tuple[Optional[str], Optional[str]]:
    """
    Load the custom Neue Haas Grotesk fonts if they exist.
    Returns (regular_family, bold_family), either of which may be None.
    """
    if not FONTS_DIR.exists():
        return None, None

    try:
        for filename in (_FONT_REGULAR, _FONT_BOLD):
            path = FONTS_DIR / filename
            if path.exists():
                _load_font_file(path)

        available      = set(tkfont.families())
        regular_family = _FAMILY_REGULAR if _FAMILY_REGULAR in available else None
        bold_family    = _FAMILY_BOLD    if _FAMILY_BOLD    in available else None

    except Exception:
        return None, None

    return regular_family, bold_family


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

class Theme:
    """
    Resolved font and colour values for the application.
    Must be constructed *after* ``tk.Tk()`` has been created.
    """

    def __init__(self) -> None:
        regular, bold = load_custom_fonts()

        self.custom_family = regular
        self._base_family  = regular or _FAMILY_FALLBACK
        self._bold_family  = bold    or _FAMILY_FALLBACK
        self.colors        = PALETTE

        # Regular-weight fonts (use _base_family with "normal")
        self.font_subtitle = (self._base_family, 14, "normal")
        self.font_body     = (self._base_family, 12, "normal")
        self.font_small    = (self._base_family, 10, "normal")
        self.font_mono     = ("Consolas",        11, "normal")

        # Bold-weight fonts (separate heavier TTF, not a style variant)
        self.font_display = (self._bold_family, 36, "normal")
        self.font_title   = (self._bold_family, 22, "normal")
        self.font_label   = (self._bold_family, 11, "normal")
        self.font_button  = (self._bold_family, 13, "normal")
        self.font_value   = (self._bold_family, 20, "normal")

    def scale(self, factor: float) -> "Theme":
        """Return a new Theme with all font sizes multiplied by *factor*."""
        def _s(spec: tuple) -> tuple:
            family, size, weight = spec
            return (family, max(8, int(size * factor)), weight)

        t = Theme.__new__(Theme)
        t.custom_family = self.custom_family
        t._base_family  = self._base_family
        t._bold_family  = self._bold_family
        t.colors        = self.colors

        t.font_display  = _s(self.font_display)
        t.font_title    = _s(self.font_title)
        t.font_subtitle = _s(self.font_subtitle)
        t.font_body     = _s(self.font_body)
        t.font_small    = _s(self.font_small)
        t.font_mono     = _s(self.font_mono)
        t.font_label    = _s(self.font_label)
        t.font_button   = _s(self.font_button)
        t.font_value    = _s(self.font_value)
        return t
