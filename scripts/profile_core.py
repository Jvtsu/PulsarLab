"""Profile the scientific pipeline with user-supplied PAR and DAT files.

The repository intentionally does not ship pulsar datasets. Pass local paths:
    python scripts/profile_core.py --par /path/to/model.par --dat /path/to/observations.dat
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile PulsarLab with a local PAR/DAT pair.")
    parser.add_argument("--par", required=True, type=Path, help="Path to a local .par model")
    parser.add_argument("--dat", required=True, type=Path, help="Path to a local .dat observations file")
    args = parser.parse_args(argv)

    dataset, report = load_pair(args.par, args.dat, args.par.name, args.dat.name)
    if dataset is None:
        print("Could not load the supplied PAR/DAT pair:")
        for message in report.errors:
            print(f"- {message}")
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
