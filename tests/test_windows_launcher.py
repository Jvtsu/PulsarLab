from __future__ import annotations

import importlib.util
from pathlib import Path


LAUNCHER = Path(__file__).parents[1] / "packaging" / "windows" / "windows_launcher.py"
SPEC = importlib.util.spec_from_file_location("pulsarlab_windows_launcher", LAUNCHER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_classify_paths_accepts_supported_files_in_any_order():
    assert MODULE.classify_paths(["x.tim", "x.par", "x.dat"]) == ("x.par", "x.dat", "x.tim")


def test_classify_paths_ignores_unknown_and_duplicate_paths():
    assert MODULE.classify_paths(["notes.txt", "first.par", "second.par"]) == ("first.par", None, None)
