from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline


def main() -> int:
    par = ROOT / "examples" / "par_files" / "nicer-paper.par"
    dat = ROOT / "examples" / "dat_files" / "nicervf_sm5-20.dat"
    dataset, report = load_pair(par, dat, par.name, dat.name)
    if dataset is None:
        print("Failed to load example")
        print(report.errors)
        return 1
    pipe = Pipeline()
    for n in (1200, 5000, 20000, 100000):
        t0 = time.perf_counter()
        pipe.compute(dataset, grid_points=n)
        first = time.perf_counter() - t0
        t1 = time.perf_counter()
        pipe.compute(dataset, grid_points=n)
        cached = time.perf_counter() - t1
        print(f"grid={n:6d} first={first*1000:8.3f} ms cached={cached*1000:8.3f} ms")
    print("Tip: install line_profiler or scalene for deeper CPU/memory traces.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
