from pathlib import Path
import ast

from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_example_pair_loads_and_computes():
    par = ROOT / "examples" / "par_files" / "nicer-paper.par"
    dat = ROOT / "examples" / "dat_files" / "nicervf_sm5-20.dat"
    ds, report = load_pair(par, dat, par.name, dat.name)
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
