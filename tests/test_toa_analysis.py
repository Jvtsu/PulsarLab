from __future__ import annotations

from pulsarlab.datasets.loader import load_project
from pulsarlab.engine.pipeline import Pipeline


def test_same_epoch_components_form_one_glitch_toa_event():
    par = """
F0 10
PEPOCH 58000
START 57990
FINISH 58020
GLEP_1 58005
GLF0_1 1e-6
GLEP_2 58005
GLF0D_2 2e-6
GLTD_2 5
"""
    tim = """
FORMAT 1
x 1400 58004 2 @
y 1400 58005.5 4 @
z 1400 58012 8 @
"""
    project, report = load_project(par_source=par, tim_source=tim)
    assert project is not None, report.errors
    result = Pipeline().compute(project, toa_window_days=2)
    assert len(result.glitch_toa_summaries) == 1
    summary = result.glitch_toa_summaries[0]
    assert summary.component_indices == (1, 2)
    assert summary.toa_count == 2
    assert summary.before_count == 1
    assert summary.after_count == 1
    assert summary.median_uncertainty_us == 3.0


def test_toa_range_lookup_remains_correct_for_hand_built_unsorted_table():
    import numpy as np
    from pulsarlab.core.types import TOATable

    table = TOATable(
        mjd=np.array([58005.0, 58001.0, 58003.0]),
        uncertainty_us=np.ones(3),
        frequency_mhz=np.full(3, 1400.0),
        names=("a", "b", "c"),
        observatories=("@", "@", "@"),
    )
    assert table.near_mjd(58003.0, 1.1).tolist() == [2]
