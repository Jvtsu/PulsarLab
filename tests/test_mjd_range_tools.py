from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

from pulsarlab.visualization.range_tools import (
    apply_mjd_range_to_figure,
    compute_visible_mjd_span,
    normalise_mjd_range,
)


def _dataset(lo, hi):
    return SimpleNamespace(observations=SimpleNamespace(mjd_span=(lo, hi)))


def test_compute_visible_mjd_span_unions_valid_datasets():
    assert compute_visible_mjd_span([_dataset(10, 20), _dataset(5, 15)]) == (5.0, 20.0)


def test_compute_visible_mjd_span_ignores_invalid_spans():
    bad = SimpleNamespace(observations=SimpleNamespace(mjd_span=(float("nan"), 12)))
    assert compute_visible_mjd_span([bad, _dataset(30, 25)]) == (25.0, 30.0)


def test_normalise_mjd_range_orders_and_expands():
    assert normalise_mjd_range(20, 10) == (10.0, 20.0)
    span = normalise_mjd_range(42, 42)
    assert span is not None
    lo, hi = span
    assert lo < 42 < hi


def test_apply_mjd_range_to_all_figure_axes():
    fig = Figure()
    ax1 = fig.subplots(1, 1)
    ax2 = ax1.twinx()
    updated = apply_mjd_range_to_figure(fig, (58000, 58100))
    assert updated == 2
    assert ax1.get_xlim() == (58000.0, 58100.0)
    assert ax2.get_xlim() == (58000.0, 58100.0)
