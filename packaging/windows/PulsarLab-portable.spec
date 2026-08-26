# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

ROOT = Path(SPECPATH).resolve().parents[1]
ICON = ROOT / "packaging" / "windows" / "pulsarlab.ico"

datas = [
    (str(ROOT / "pulsarlab" / "i18n"), "pulsarlab/i18n"),
    (str(ROOT / "examples"), "examples"),
]

hiddenimports = [
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_qt",
    "PySide6.QtPrintSupport",
    "PySide6.QtSvg",
]

excludes = [
    "astropy",
    "pint",
    "numba",
    "polars",
    "pyarrow",
    "h5py",
    "zarr",
    "pyqtgraph",
    "pytest",
]

a = Analysis(
    [str(ROOT / "packaging" / "windows" / "windows_launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={"matplotlib": {"backends": "QtAgg"}},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PulsarLab-Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if sys.platform == "win32" else None,
)
