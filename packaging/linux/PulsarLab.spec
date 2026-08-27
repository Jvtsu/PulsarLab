# -*- mode: python ; coding: utf-8 -*-

"""
Archivo de configuración PyInstaller para PulsarLab (Linux).

Compilación:
    pyinstaller packaging/linux/PulsarLab.spec

Formato:
    --onedir

Genera dist/PulsarLab/ con el ejecutable, sus bibliotecas nativas
(incluyendo el runtime de Qt que trae PySide6) y los datos empaquetados.
No requiere Python instalado en la máquina destino.
"""

from pathlib import Path


# Directorio raíz del proyecto.
# SPECPATH ya es el directorio "packaging/linux" (sin nombre de archivo),
# por lo que solo se necesitan dos ".parent" para llegar a la raíz del repo:
#   packaging/linux -> packaging -> ROOT
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

    # Sin icono: Linux no incrusta iconos en el binario ELF vía PyInstaller;
    # el acceso directo/.desktop del escritorio es responsabilidad del
    # empaquetado (rpm/deb/AppImage), no de este spec.
)


coll = COLLECT(

    exe,

    a.binaries,

    a.datas,

    strip=False,

    upx=True,

    name="PulsarLab"

)
