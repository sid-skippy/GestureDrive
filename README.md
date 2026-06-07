# GestureDrive

![GestureDrive](docs/images/6.png)

Control racing games using hand gestures and a standard webcam.

GestureDrive uses MediaPipe hand tracking and a virtual Xbox controller to convert natural hand movements into steering, throttle, braking, handbrake and gear controls.

No gloves. No controllers. Just a webcam.

---

## Features

* Real-time hand tracking using MediaPipe
* Gesture-based steering
* Analog throttle and brake control
* Handbrake gesture
* Gear up and gear down gestures
* Interactive tutorial and calibration wizard
* Virtual Xbox controller emulation
* Customizable control sensitivity
* Modern desktop interface
* Windows executable builds

---

## Screenshots

### Welcome Screen

![Welcome Screen](docs/images/1.png)

### Calibration Wizard

![Calibration Wizard](docs/images/3.png)

### Settings

![Settings](docs/images/2.png)

### Runtime

![Runtime](docs/images/5.png)

---

## Controls

| Gesture                   | Action    |
| ------------------------- | --------- |
| Tilt left hand            | Steering  |
| Open left hand            | Handbrake |
| Raise right thumb         | Throttle  |
| Lower right thumb         | Brake     |
| Raise right index finger  | Gear Up   |
| Raise right little finger | Gear Down |

---

## Requirements

* Windows 10 / Windows 11
* Webcam (30 FPS recommended)
* ViGEm Bus Driver

Install ViGEm Bus:

https://github.com/nefarius/ViGEmBus/releases

---

## Installation

### Download Release

1. Download the latest release.
2. Install the ViGEm Bus Driver.
3. Launch GestureDrive.
4. Complete the tutorial and calibration process.
5. Start your game.

---

## Running From Source

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

---

## Building

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Build:

```bash
pyinstaller GestureDrive.spec
```

The executable will be generated in:

```text
dist/GestureDrive/
```

---

## Supported Games

GestureDrive works with games that support Xbox controllers.

Tested with:

* Forza Horizon 4
* Forza Horizon 5
* Need for Speed Unbound

Additional games may also work.

---

## Known Limitations

* Requires adequate lighting
* Works best with a plain background
* Webcam quality affects tracking performance
* Windows only

---

## Credits

* MediaPipe
* OpenCV
* vgamepad
* ViGEmBus
* Pillow

---

## License

Released under the MIT License.
See the LICENSE file for details.
