from __future__ import annotations

import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import time
import numpy as np

from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline

par = """
PSRJ JBENCH
F0 10
F1 -1e-10
PEPOCH 58000
START 58000
FINISH 58100
GLEP_1 58050
GLF0_1 1e-6
"""

mjd = np.linspace(58000, 58100, 20000)
f0 = 10 - 1e-10 * (mjd - 58000) * 86400
err = np.full_like(mjd, 1e-9)
dat = "\n".join(f"{a:.8f} {b:.12f} {c:.3e}" for a, b, c in zip(mjd, f0, err))

ds, report = load_pair(par, dat, "bench.par", "bench.dat")
if ds is None:
    raise SystemExit(report.errors)
pipe = Pipeline()
t0 = time.perf_counter()
pipe.compute(ds, grid_points=2000)
t1 = time.perf_counter()
pipe.compute(ds, grid_points=2000)
t2 = time.perf_counter()
print(f"First compute: {(t1-t0)*1000:.1f} ms")
print(f"Cached compute: {(t2-t1)*1000:.3f} ms")
