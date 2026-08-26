# -*- mode: python ; coding: utf-8 -*-

"""
Archivo de configuración PyInstaller para PulsarLab.

Compilación:
pyinstaller PulsarLab-folder.spec

Formato:
--onedir

Este formato mantiene las DLL externas separadas,
reduciendo problemas con:
- NumPy
- Matplotlib
- PySide6
- Qt plugins
"""

from pathlib import Path


# Directorio raíz del proyecto
ROOT = Path(SPECPATH).resolve().parent.parent.parent


# Recursos adicionales que deben copiarse al bundle final
datas = [

    # Datos de ejemplo para pruebas del usuario
    (
        str(ROOT / "examples"),
        "examples"
    ),

    # Archivos de internacionalización
    (
        str(ROOT / "pulsarlab" / "i18n"),
        "pulsarlab/i18n"
    ),
]


# Importaciones dinámicas necesarias para evitar
# errores silenciosos al ejecutar la aplicación.
hiddenimports = [

    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "PySide6",

]


a = Analysis(

    # Punto de entrada principal de PulsarLab
    [
        str(ROOT / "pulsarlab" / "cli" / "launch.py")
    ],

    pathex=[
        str(ROOT)
    ],

    binaries=[],

    datas=datas,

    hiddenimports=hiddenimports,

    hookspath=[],

    hooksconfig={},

    runtime_hooks=[],

    excludes=[],

    noarchive=False,
)


pyz = PYZ(
    a.pure
)


exe = EXE(

    pyz,

    a.scripts,

    [],

    exclude_binaries=True,

    name="PulsarLab",

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=True,

    console=False,

    icon=str(ROOT / "packaging" / "windows" / "pulsarlab.ico")

)


coll = COLLECT(

    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=True,

    name="PulsarLab"

)