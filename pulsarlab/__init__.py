"""PulsarLab.

Scientific pulsar spin-evolution, glitch, and TOA-context analysis platform.
Headless layers remain importable without PySide6.

The package metadata in ``pyproject.toml`` is the single version source. When
PulsarLab is installed, read the version from distribution metadata; when run
straight from a source checkout, fall back to that same ``pyproject.toml``.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path

try:
    __version__ = distribution_version("pulsarlab")
except PackageNotFoundError:
    _project_file = Path(__file__).resolve().parent.parent / "pyproject.toml"
    _match = re.search(r'^version\s*=\s*"([^\"]+)"\s*$', _project_file.read_text(encoding="utf-8"), re.MULTILINE)
    if _match is None:
        raise RuntimeError(f"Could not determine PulsarLab version from {_project_file}")
    __version__ = _match.group(1)

__all__ = ["__version__"]
