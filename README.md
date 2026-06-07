# GestureDrive

> Hand-gesture virtual gamepad for **Forza Horizon** (and any Xbox-compatible game).
> Built with MediaPipe + vgamepad. Packaged as a polished desktop app.

---

## Project Structure

```
GestureDrive/
├── main.py                  ← Entry point
├── requirements.txt
├── GestureDrive.spec        ← PyInstaller build spec
│
├── gesturedrive/
│   ├── app.py               ← Application controller / screen router
│   │
│   ├── ui/
│   │   ├── theme.py         ← Colour palette + font loading
│   │   ├── widgets.py       ← GDButton, GDBar, GDSlider, etc.
│   │   ├── welcome.py       ← Welcome / hero screen
│   │   ├── runtime.py       ← Live driving screen
│   │   └── settings_screen.py
│   │
│   ├── calibration/
│   │   └── wizard.py        ← 5-step guided calibration wizard
│   │
│   ├── gestures/
│   │   └── engine.py        ← All gesture logic (preserved from original)
│   │
│   ├── settings/
│   │   └── manager.py       ← config.json read/write
│   │
│   └── config/
│       └── paths.py         ← Centralised path resolution (dev + frozen)
│
├── assets/
│   └── icons/               ← icon.png / icon.ico (optional, add your own)
│
├── fonts/                   ← Drop .ttf files here (Rajdhani recommended)
│   └── README.txt
│
├── config/                  ← Auto-created at runtime
│   ├── config.json
│   └── calibration.json
│
└── hand_landmarker.task     ← MediaPipe model (REQUIRED — download separately)
```

---

## Prerequisites

### 1. Python 3.10 or 3.11 (64-bit, Windows)

### 2. ViGEmBus driver (required for vgamepad)
Download and install from:
https://github.com/nefarius/ViGEmBus/releases

### 3. MediaPipe hand landmark model
Download `hand_landmarker.task` from:
https://developers.google.com/mediapipe/solutions/vision/hand_landmarker#models

Place it in the project root (same folder as `main.py`).

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

---

## Running in Development

```bash
python main.py
```

---

## Custom Fonts (Optional but Recommended)

GestureDrive looks best with **Rajdhani** (free on Google Fonts):
https://fonts.google.com/specimen/Rajdhani

Download and place the `.ttf` files into the `fonts/` directory:
```
fonts/
  Rajdhani-Regular.ttf
  Rajdhani-SemiBold.ttf
  Rajdhani-Bold.ttf
```

The application will auto-detect and load them. Falls back to **Segoe UI** if missing.

---

## Building the Windows Executable

### Step 1 — Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2 — Build
```bash
pyinstaller GestureDrive.spec
```

### Step 3 — Find your release
```
dist/
  GestureDrive/
    GestureDrive.exe   ← Launch this
    (all bundled DLLs and assets)
```

### Step 4 — Distribute
Zip the entire `dist/GestureDrive/` folder and share it.
Users need ViGEmBus installed — nothing else.

---

## Packaging Notes

- `hand_landmarker.task` must exist in the project root **before** building.
- Fonts in `fonts/` are bundled automatically by the `.spec`.
- `config/` directory is created next to the `.exe` on first run — it is writable even when the rest of the bundle is read-only.
- If you add an app icon: convert to `.ico`, place it at `assets/icons/icon.ico`, and uncomment the `icon=` line in `GestureDrive.spec`.

---

## Gesture Reference

| Hand  | Gesture               | Action      |
|-------|-----------------------|-------------|
| Left  | Thumb tilt left/right | Steering    |
| Left  | Pinky extended        | Handbrake   |
| Right | Thumb raised          | Throttle    |
| Right | Thumb on index finger | Brake       |
| Right | Index finger extended | Gear Up     |
| Right | Pinky extended        | Gear Down   |

---

## Settings

All settings are saved to `config/config.json` automatically.

| Setting              | Default | Range      | Description                        |
|----------------------|---------|------------|------------------------------------|
| steering_sensitivity | 1.0     | 0.3 – 3.0  | Multiplier for steering input      |
| throttle_sensitivity | 1.0     | 0.3 – 3.0  | Multiplier for throttle input      |
| dead_zone            | 0.25    | 0.0 – 0.5  | Steering centre dead zone          |
| smoothing            | 0.2     | 0.05 – 0.95| Exponential smoothing factor       |
| camera_index         | 0       | 0 – 5      | OpenCV camera index                |
| fps_limit            | 60      | 15 – 120   | Target frame rate                  |
| ui_scale             | 1.0     | 0.75 – 2.0 | UI font/element scaling            |

---

## Troubleshooting

**"Camera not found"**
→ Check `camera_index` in Settings. Try 0, 1, 2.

**"MediaPipe model missing"**
→ Download `hand_landmarker.task` and place it next to `main.py` (or the `.exe`).

**Gamepad not working in game**
→ Ensure ViGEmBus is installed and the game is set to "Xbox controller" input.

**Hands not detected**
→ Improve lighting. Avoid dark backgrounds. Keep hands 50–80 cm from camera.

**App freezes on exit**
→ Always use the ✕ Exit button inside the app rather than closing the window directly.
