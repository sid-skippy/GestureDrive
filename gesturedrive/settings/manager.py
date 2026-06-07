import json

from ..config.paths import CONFIG_FILE


# ---------------------------------------------------------------------------
# Defaults and bounds
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    "smoothing":            0.50,
    "steering_sensitivity": 1.0,
    "throttle_sensitivity": 1.0,
    "dead_zone":            0.40,
    "pinky_threshold":      0.20,
    "index_threshold":      0.20,
    "camera_index":         0,
    "fps_limit":            30,
    "ui_scale":             1.0,
    "handbrake_button":     "A",
    "gear_up_button":       "B",
    "gear_down_button":     "X",
}

BOUNDS: dict = {
    "smoothing":            (0.05, 0.95),
    "steering_sensitivity": (0.3,  3.0),
    "throttle_sensitivity": (0.3,  3.0),
    "dead_zone":            (0.0,  0.5),
    "pinky_threshold":      (0.05, 0.30),
    "index_threshold":      (0.05, 0.30),
    "camera_index":         (0,    10),
    "fps_limit":            (15,   120),
    "ui_scale":             (0.75, 2.0),
}


# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------

class SettingsManager:
    """Loads, validates, mutates and persists application settings."""

    def __init__(self) -> None:
        self._data: dict = {}
        self.load()

    # -- I/O -------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk, falling back to defaults on any error."""
        self._data = dict(DEFAULTS)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    stored = json.load(f)
                for key, value in stored.items():
                    if key in DEFAULTS:
                        self._data[key] = value
            except Exception:
                pass  # corrupt file — silently use defaults

    def save(self) -> None:
        """Persist current settings to disk."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    # -- accessors -------------------------------------------------------------

    def get(self, key: str, fallback=None):
        """Return the value for *key*, or *fallback* / the default if absent."""
        return self._data.get(key, fallback if fallback is not None else DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        """Set *key* to *value*, clamping to BOUNDS if applicable."""
        if key in BOUNDS:
            lo, hi = BOUNDS[key]
            value  = max(lo, min(hi, value))
        self._data[key] = value

    def as_dict(self) -> dict:
        """Return a shallow copy of the current settings."""
        return dict(self._data)

    def reset_defaults(self) -> None:
        """Reset all settings to factory defaults and save."""
        self._data = dict(DEFAULTS)
        self.save()

    # -- convenience properties ------------------------------------------------

    @property
    def camera_index(self) -> int:
        return int(self._data.get("camera_index", 0))

    @property
    def fps_limit(self) -> int:
        return int(self._data.get("fps_limit", 30))
