import sys
from pathlib import Path


def _base() -> Path:
    """Return the base directory whether running frozen or in dev."""
    if getattr(sys, "frozen", False):
        # PyInstaller sets sys._MEIPASS to the temp extraction folder
        return Path(sys._MEIPASS)          # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


BASE_DIR     = _base()
ASSETS_DIR   = BASE_DIR / "assets"
FONTS_DIR    = BASE_DIR / "fonts"
CONFIG_DIR   = BASE_DIR / "config"

# Runtime-writable paths live next to the exe (or cwd in dev)
_WRITE_BASE  = Path(sys.executable).parent if getattr(sys, "frozen", False) else BASE_DIR

CONFIG_FILE  = _WRITE_BASE / "config" / "config.json"
CALIB_FILE   = _WRITE_BASE / "config" / "calibration.json"
MODEL_FILE   = BASE_DIR / "hand_landmarker.task"
SETUP_IMAGES_DIR = ASSETS_DIR / "setup"
