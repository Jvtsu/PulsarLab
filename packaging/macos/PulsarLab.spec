# -*- mode: python ; coding: utf-8 -*-

"""
Archivo de configuración PyInstaller para PulsarLab (macOS).

Compilación:
    pyinstaller packaging/macos/PulsarLab.spec

Formato:
    --onedir

Genera:
    dist/PulsarLab/       -> carpeta --onedir (ejecutable + librerías)
    dist/PulsarLab.app    -> paquete de aplicación de doble clic que
                             envuelve la carpeta anterior

No requiere Python instalado en la máquina destino.
"""

from pathlib import Path
import os
import re


# Directorio raíz del proyecto.
# SPECPATH ya es el directorio "packaging/macos" (sin nombre de archivo),
# por lo que solo se necesitan dos ".parent" para llegar a la raíz del repo:
#   packaging/macos -> packaging -> ROOT
ROOT = Path(SPECPATH).resolve().parent.parent


# CI supplies APP_VERSION; direct local builds read the same project metadata.
_project_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
_version_match = re.search(r'^version\s*=\s*"([^\"]+)"\s*$', _project_text, re.MULTILINE)
if _version_match is None:
    raise RuntimeError("Could not read project version from pyproject.toml")
APP_VERSION = os.environ.get("APP_VERSION", _version_match.group(1))

# Only application-owned package resources are bundled; user PAR/DAT/TIM
# datasets are deliberately not distributed with the application.
datas = [

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

    upx=False,

    console=False,
)


coll = COLLECT(

    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=False,

    name="PulsarLab"

)


# PyInstaller normaliza el PNG a ICNS usando Pillow (instalado como
# dependencia de Matplotlib) antes de crear el bundle de macOS.
app = BUNDLE(

    coll,

    name="PulsarLab.app",

    icon=str(ROOT / "packaging" / "windows" / "pulsarlab.png"),

    bundle_identifier="dev.pulsarlab.app",

    info_plist={
        "CFBundleName": "PulsarLab",
        "CFBundleDisplayName": "PulsarLab",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
    },
)
