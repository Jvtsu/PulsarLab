from pathlib import Path
import ast

from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline
from sample_data import sample_sources

ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_par_dat_pair_loads_and_computes():
    par, dat, _tim = sample_sources()
    ds, report = load_pair(par, dat, "synthetic.par", "synthetic.dat")
    assert ds is not None, report.errors
    res = Pipeline().compute(ds, grid_points=256)
    assert res.model_mjd.size >= 256
    assert res.stats_f0.n == ds.n_observations


def test_no_qt_imports_in_headless_layers():
    checked_dirs = ["core", "parsers", "datasets", "engine", "visualization", "state", "utils"]
    offenders = []
    for dirname in checked_dirs:
        for file in (ROOT / "pulsarlab" / dirname).glob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = []
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    else:
                        names = [node.module or ""]
                    if any(name.startswith("PySide6") or name.startswith("Qt") for name in names):
                        offenders.append(str(file.relative_to(ROOT)))
    assert not offenders


def test_repository_does_not_ship_user_timing_datasets():
    forbidden = {".par", ".dat", ".tim"}
    excluded_dirs = {".git", ".venv", ".venv-build", "build", "dist", "__pycache__", ".pytest_cache", ".hypothesis"}
    found = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded_dirs for part in path.parts):
            continue
        if path.suffix.lower() in forbidden:
            found.append(str(path.relative_to(ROOT)))
    assert not found, f"User timing data must not be distributed: {found}"
