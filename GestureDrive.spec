# GestureDrive.spec
# PyInstaller build file — single-folder release (onedir)
import sys
import os
import site
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821

# ── Locate site-packages ──────────────────────────────────────────────────────
def _site():
    for sp in site.getsitepackages():
        if Path(sp).name == "site-packages":
            return Path(sp)
    return Path(site.getsitepackages()[0])

SITE = _site()

# ── Collect mediapipe data files (models, .pbtxt, .tflite, etc.) ──────────────
# PyInstaller misses these because mediapipe uses importlib.resources internally.
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

mediapipe_datas = collect_data_files("mediapipe", include_py_files=True)
mediapipe_bins = collect_dynamic_libs("mediapipe")

# ── Collect vgamepad ViGEmClient.dll tree ─────────────────────────────────────
def _find_vgamepad_dlls():
    results = []
    vigem_dir = SITE / "vgamepad" / "win" / "vigem"
    if vigem_dir.exists():
        for dll in vigem_dir.rglob("*.dll"):
            dest = str(dll.relative_to(SITE).parent)
            results.append((str(dll), dest))
    return results

vgamepad_binaries = _find_vgamepad_dlls()

# ── Data files ────────────────────────────────────────────────────────────────
ASSETS_ROOT = ROOT / "gesturedrive" / "assets"

asset_datas = [
    (str(f), str(Path("assets") / f.relative_to(ASSETS_ROOT).parent))
    for f in ASSETS_ROOT.rglob("*")
    if f.is_file()
]

fonts_dir = ROOT / "fonts"
font_datas = [(str(f), "fonts") for f in fonts_dir.glob("*.ttf")] if fonts_dir.exists() else []

task_file = ROOT / "hand_landmarker.task"
task_datas = [(str(task_file), ".")] if task_file.exists() else []

datas = mediapipe_datas + task_datas + font_datas + asset_datas

# ── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # mediapipe
    "mediapipe",
    "mediapipe.tasks",
    "mediapipe.tasks.python",
    "mediapipe.tasks.python.vision",
    "mediapipe.tasks.python.core",
    "mediapipe.tasks.python.core.base_options",
    "mediapipe.python",
    "mediapipe.python._framework_bindings",
    # mediapipe deps
    "flatbuffers",
    "absl",
    "absl.flags",
    "absl.logging",
    "attr",
    "attrs",
    "google.protobuf",
    "google.protobuf.descriptor",
    "google.protobuf.descriptor_pool",
    "google.protobuf.message",
    "google.protobuf.reflection",
    "google.protobuf.symbol_database",
    # cv2 / PIL
    "cv2",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    # gamepad
    "vgamepad",
    # stdlib
    "numpy",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.font",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=mediapipe_bins + vgamepad_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["scipy", "pandas", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GestureDrive",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestureDrive",
)
