"""Reproducible large-dataset benchmark for TIM parsing and TOA search."""

from __future__ import annotations

import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pulsarlab.datasets.loader import load_project
from pulsarlab.engine.pipeline import Pipeline
from pulsarlab.parsers.tim_parser import parse_tim


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:.3f} ms"


def main() -> int:
    par = """
PSRJ JBENCH-LARGE
F0 10
F1 -1e-10
PEPOCH 58000
START 58000
FINISH 58100
GLEP_1 58025
GLF0_1 1e-6
GLEP_2 58050
GLF0_2 2e-6
GLEP_3 58075
GLF0D_3 1e-6
GLTD_3 10
"""
    n_toas = 100_000
    mjd = np.linspace(58000, 58100, n_toas)
    tim = "FORMAT 1\n" + "\n".join(
        f"toa{i} 1400 {epoch:.12f} 2.0 @ -pn {i}"
        for i, epoch in enumerate(mjd)
    )

    t0 = time.perf_counter()
    toas, report = parse_tim(tim, "benchmark.tim")
    t1 = time.perf_counter()
    if toas is None:
        print(report.errors)
        return 1

    project, project_report = load_project(
        par_source=par,
        tim_source=tim,
        par_filename="benchmark.par",
        tim_filename="benchmark.tim",
    )
    t2 = time.perf_counter()
    if project is None:
        print(project_report.errors)
        return 1

    pipe = Pipeline()
    result = pipe.compute(project, grid_points=20_000, toa_window_days=30)
    t3 = time.perf_counter()
    pipe.compute(project, grid_points=20_000, toa_window_days=30)
    t4 = time.perf_counter()

    search_start = time.perf_counter()
    for epoch in (58025.0, 58050.0, 58075.0):
        toas.near_mjd(epoch, 30.0)
    search_end = time.perf_counter()

    print("PulsarLab benchmark")
    print(f"TIM rows: {n_toas:,}")
    print(f"TIM parse: {_ms(t1 - t0)}")
    print(f"Project assembly (PAR+TIM): {_ms(t2 - t1)}")
    print(f"Pipeline first compute: {_ms(t3 - t2)}")
    print(f"Pipeline cached compute: {_ms(t4 - t3)}")
    print(f"Three TOA window searches: {_ms(search_end - search_start)}")
    print(f"Glitch events summarized: {len(result.glitch_toa_summaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
