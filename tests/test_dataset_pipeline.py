import time
import numpy as np

from pulsarlab.datasets.loader import load_pair
from pulsarlab.datasets.manager import DatasetManager
from pulsarlab.engine.pipeline import Pipeline


def synthetic_pair(n=80):
    par = """
PSRJ JTEST
F0 10
F1 -1e-10
PEPOCH 58000
START 58000
FINISH 58010
GLEP_1 58005
GLF0_1 1e-6
"""
    mjd = np.linspace(58000, 58010, n)
    f0 = 10 + (-1e-10) * (mjd - 58000) * 86400
    err = np.full_like(mjd, 1e-9)
    dat = "\n".join(f"{a:.8f} {b:.12f} {c:.3e}" for a, b, c in zip(mjd, f0, err))
    return par, dat


def test_load_pair_filters_and_pipeline_cache():
    par, dat = synthetic_pair()
    ds, report = load_pair(par, dat, "a.par", "a.dat")
    assert ds is not None, report.errors
    pipe = Pipeline()
    r1 = pipe.compute(ds)
    r2 = pipe.compute(ds)
    assert r1 is r2
    assert r1.model_mjd.size >= 1200
    assert r1.residual_f0.size == ds.n_observations


def test_dataset_visibility_state_no_crash():
    par, dat = synthetic_pair()
    ds1, report1 = load_pair(par, dat, "a.par", "a.dat", dataset_id="d1")
    ds2, report2 = load_pair(par, dat, "b.par", "b.dat", dataset_id="d2")
    assert ds1 is not None, report1.errors
    assert ds2 is not None, report2.errors
    manager = DatasetManager()
    manager.add(ds1)
    manager.add(ds2)
    assert len(manager.visible()) == 2
    manager.set_visible("d2", False)
    assert len(manager.visible()) == 1
    manager.active_id = "d2"
    assert manager.active_id == "d1"
    manager.set_visible("d1", False)
    assert manager.active_id is None
    manager.set_visible("d2", True)
    assert manager.active_id == "d2"


def test_performance_smoke_under_reasonable_time():
    par, dat = synthetic_pair(n=5000)
    ds, report = load_pair(par, dat, "large.par", "large.dat")
    assert ds is not None, report.errors
    pipe = Pipeline()
    t0 = time.perf_counter()
    pipe.compute(ds, grid_points=1500)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0
