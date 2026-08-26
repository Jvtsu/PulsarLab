"""
Utilidades generales de PulsarLab.

Incluye funciones necesarias para compatibilidad entre:
- Ejecución directa desde código fuente.
- Ejecución empaquetada mediante PyInstaller (--onedir).

PyInstaller almacena los recursos temporales dentro de sys._MEIPASS,
por lo que esta función permite resolver rutas correctamente en ambos casos.
"""

from pathlib import Path
import sys


def resource_path(relative_path: str) -> Path:
    """
    Obtiene la ruta absoluta de un recurso incluido en la aplicación.

    Parámetros
    ----------
    relative_path : str
        Ruta relativa del recurso dentro del proyecto.

    Retorna
    -------
    Path
        Ruta absoluta válida para ejecución normal o PyInstaller.
    """

    # Cuando la aplicación está empaquetada con PyInstaller,
    # los recursos se extraen temporalmente dentro de _MEIPASS.
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)

    # Ejecución normal desde el código fuente.
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path