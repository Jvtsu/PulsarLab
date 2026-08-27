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


# Directorio raíz del proyecto.
# SPECPATH ya es el directorio "packaging/macos" (sin nombre de archivo),
# por lo que solo se necesitan dos ".parent" para llegar a la raíz del repo:
#   packaging/macos -> packaging -> ROOT
ROOT = Path(SPECPATH).resolve().parent.parent


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
)


coll = COLLECT(

    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=True,

    name="PulsarLab"

)


# Paquete .app de macOS. PyInstaller convierte automáticamente un PNG a
# .icns en tiempo de compilación (usa las herramientas sips/iconutil,
# preinstaladas en los runners macos-latest), así que se reutiliza el
# PNG existente en lugar de duplicar un asset .icns.
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
    },
)
