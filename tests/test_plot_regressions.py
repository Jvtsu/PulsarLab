"""Regression tests for the issues reported from macOS testing.

Each test pins one reported symptom: invisible tick numbers, missing error
bars, missing observed ΔF0/ΔF1 data, residual definition, clipped labels.
"""

from __future__ import annotations

import warnings
from dataclasses import replace

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure

from pulsarlab.datasets.loader import load_project
from pulsarlab.engine.pipeline import Pipeline
from pulsarlab.visualization import matplotlib_plots as P
from sample_data import sample_sources


def _project(with_tim: bool = True):
    par, dat, tim = sample_sources(with_tim=with_tim)
    kwargs = dict(par_source=par, par_filename="synthetic.par", dat_source=dat, dat_filename="synthetic.dat")
    if with_tim and tim is not None:
        kwargs.update(tim_source=tim, tim_filename="synthetic.tim")
    project, report = load_project(**kwargs)
    assert project is not None, report.errors
    return project


def _compute(project):
    return {project.dataset_id: Pipeline().compute(project, toa_window_days=30, summarize_toas=True)}


def _panels(*names):
    keys = ("f0", "f1", "phase", "delta_f0", "delta_f1")
    return {k: k in names for k in keys}


def _fig(size=(11, 6)):
    fig = Figure(figsize=size, dpi=100)
    FigureCanvasAgg(fig)
    return fig


def _luminance(color) -> float:
    r, g, b = to_rgb(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _errorbar_containers(ax):
    return [c for c in ax.containers if hasattr(c, "has_yerr")]


def _bar_half_lengths(container):
    segments = container.lines[2][0].get_segments()
    return np.array([abs(seg[1][1] - seg[0][1]) / 2 for seg in segments])


# --------------------------------------------------------------- tick numbers
def test_every_tick_label_is_light_on_dark_including_minor_log_ticks():
    project = _project()
    fig = _fig()
    P.plot_glitches_toas(fig, [project], _compute(project), toa_window=30.0)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    checked = 0
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for label in axis.get_ticklabels(which="both"):
                if label.get_text() and label.get_visible() and label.get_window_extent(renderer).width > 0:
                    assert _luminance(label.get_color()) > 0.35, (label.get_text(), label.get_color())
                    checked += 1
    assert checked > 0


def test_uncertainty_axis_has_visible_numbers_when_range_is_under_one_decade():
    project = _project()
    t = project.toas
    # sigma confined to 40-90 us: no decade boundary inside the view
    sigma = np.linspace(40.0, 90.0, t.n)
    project = project.with_toas(replace(t, uncertainty_us=sigma))
    fig = _fig()
    P.plot_glitches_toas(fig, [project], _compute(project), toa_window=30.0)
    fig.canvas.draw()
    ax = fig.axes[1]
    lo, hi = ax.get_ylim()
    labelled = []
    for minor in (False, True):
        labels = ax.yaxis.get_ticklabels(minor=minor)
        locs = ax.yaxis.get_ticklocs(minor=minor)
        labelled += [lbl for lbl, loc in zip(labels, locs) if lo <= loc <= hi and lbl.get_text()]
    assert labelled, "no y numbers at all on the sigma(TOA) axis"
    assert all(_luminance(lbl.get_color()) > 0.35 for lbl in labelled)


@pytest.mark.parametrize("mode", ["no_tim", "sigma_zero"])
def test_mjd_numbers_survive_empty_uncertainty_panel(mode):
    project = _project(with_tim=(mode != "no_tim"))
    if mode == "sigma_zero":
        project = project.with_toas(replace(project.toas, uncertainty_us=np.zeros_like(project.toas.uncertainty_us)))
    fig = _fig()
    P.plot_glitches_toas(fig, [project], _compute(project), toa_window=30.0)
    fig.canvas.draw()
    bottom = fig.axes[1]
    assert len(bottom.get_xticks()) > 1
    assert any(t.get_text() for t in bottom.get_xticklabels())


def test_toa_window_band_is_explained_in_the_legend():
    project = _project()
    fig = _fig()
    P.plot_glitches_toas(fig, [project], _compute(project), toa_window=30.0)
    texts = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert any("TOA window" in t and "30" in t for t in texts), texts


# ------------------------------------------------------------------ error bars
def test_residuals_have_error_bars_equal_to_dat_uncertainty():
    project = _project()
    results = _compute(project)
    fig = _fig()
    P.plot_residuals(fig, [project], results)
    obs = project.observations
    f0 = _errorbar_containers(fig.axes[0])
    assert len(f0) == 1
    np.testing.assert_allclose(_bar_half_lengths(f0[0]), obs.f0_err[np.isfinite(obs.f0_err)], rtol=1e-9)
    f1 = _errorbar_containers(fig.axes[1])
    assert len(f1) == 1
    np.testing.assert_allclose(_bar_half_lengths(f1[0]), obs.f1_err[np.isfinite(obs.f1_err)] * 1e15, rtol=1e-9)


def test_error_bars_can_be_hidden():
    project = _project()
    fig = _fig()
    P.plot_residuals(fig, [project], _compute(project), visibility={"errorbars": False})
    container = _errorbar_containers(fig.axes[0])[0]
    assert not container.has_yerr


def test_summary_view_and_spin_view_draw_error_bars():
    project = _project()
    results = _compute(project)
    fig = _fig()
    P.plot_dataset_summary(fig, [project], results)
    assert _errorbar_containers(fig.axes[0])
    fig = _fig()
    P.plot_spin_analysis(fig, [project], results, panels=_panels("f0", "f1", "delta_f0", "delta_f1"))
    for ax in fig.axes:
        assert any(c.has_yerr for c in _errorbar_containers(ax)), ax.get_ylabel()


# --------------------------------------------------------- observed ΔF0 / ΔF1
def test_pipeline_observed_delta_is_data_minus_noglitch_model():
    project = _project()
    result = _compute(project)[project.dataset_id]
    obs = project.observations
    np.testing.assert_allclose(result.delta_f0_obs, obs.f0 - result.f0_noglit_at_data, rtol=0, atol=1e-15)
    np.testing.assert_allclose(result.delta_f1_obs, obs.f1 - result.f1_noglit_at_data, rtol=0, atol=1e-22)
    # and it differs from the residual exactly by the model's glitch contribution
    glitch_at_data = result.f0_at_data - result.f0_noglit_at_data
    np.testing.assert_allclose(result.delta_f0_obs - glitch_at_data, result.residual_f0, atol=1e-14)


def test_delta_panels_show_observed_dat_points():
    project = _project()
    results = _compute(project)
    result = results[project.dataset_id]
    fig = _fig()
    P.plot_spin_analysis(fig, [project], results, panels=_panels("delta_f0", "delta_f1"))
    ax0, ax1 = fig.axes[:2]
    c0 = _errorbar_containers(ax0)
    assert c0, "no observed points in the ΔF0 panel"
    np.testing.assert_allclose(c0[0].lines[0].get_ydata(), result.delta_f0_obs)
    c1 = _errorbar_containers(ax1)
    assert c1, "no observed points in the ΔF1 panel"
    np.testing.assert_allclose(c1[0].lines[0].get_ydata(), result.delta_f1_obs * 1e15)


def test_delta_observed_points_follow_visibility_toggle():
    project = _project()
    results = _compute(project)
    fig = _fig()
    artists = P.plot_spin_analysis(
        fig, [project], results, panels=_panels("delta_f0", "delta_f1"),
        visibility={"D1 ΔF0 obs": False, "D1 ΔF1 model": False},
    )
    assert not artists["D1 ΔF0 obs"].lines[0].get_visible()
    assert artists["D1 ΔF0 model"].get_visible()
    assert not artists["D1 ΔF1 model"].get_visible()


# ---------------------------------------------------------------- residuals
def test_residual_is_exactly_observed_minus_model_with_glitches():
    """Guards the user's question: nothing else is subtracted."""
    project = _project()
    result = _compute(project)[project.dataset_id]
    obs = project.observations
    np.testing.assert_allclose(result.residual_f0, obs.f0 - result.f0_at_data, rtol=0, atol=1e-15)
    np.testing.assert_allclose(result.residual_f1, obs.f1 - result.f1_at_data, rtol=0, atol=1e-22)


def test_residual_axes_are_not_named_like_the_spin_delta_panels():
    project = _project()
    fig = _fig()
    P.plot_residuals(fig, [project], _compute(project))
    assert "residual" in fig.axes[0].get_ylabel().lower()
    assert "Δ" not in fig.axes[0].get_ylabel()


# ------------------------------------------------------------------- layout
@pytest.mark.parametrize("size", [(11, 6), (8, 4.2), (7, 3.6)])
@pytest.mark.parametrize("view", ["spin2", "spin5", "glitches", "residuals"])
def test_labels_are_not_clipped_at_small_canvas_sizes(view, size):
    project = _project()
    results = _compute(project)
    fig = _fig(size)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # constrained layout collapse would warn
        if view == "spin2":
            P.plot_spin_analysis(fig, [project], results)
        elif view == "spin5":
            if size[1] < 5:
                pytest.skip("5 stacked panels need a taller canvas")
            P.plot_spin_analysis(fig, [project], results, panels=_panels("f0", "f1", "phase", "delta_f0", "delta_f1"))
        elif view == "glitches":
            P.plot_glitches_toas(fig, [project], results, toa_window=30.0)
        else:
            P.plot_residuals(fig, [project], results)
        fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figbox = fig.bbox
    bottom = fig.axes[-1] if view != "spin5" else fig.axes[4]
    artists = [bottom.xaxis.label, fig.axes[0].title] if fig.axes[0].get_title() else [bottom.xaxis.label]
    for art in artists:
        if art.get_text():
            box = art.get_window_extent(renderer)
            assert box.y0 >= figbox.y0 - 1 and box.y1 <= figbox.y1 + 1, (art.get_text(), box, figbox)


# ------------------------------------------- two datasets, with and without TIM
def _vela(with_tim: bool):
    par, dat, tim = sample_sources(
        psr="J0835-4510", f0=11.2, f1=-1.55e-11,
        f0_error=1.0e-13, noise_amplitude=1.0e-6, with_tim=with_tim,
    )
    kw = dict(par_source=par, par_filename="synthetic-vela.par",
              dat_source=dat, dat_filename="synthetic-vela.dat")
    if with_tim and tim is not None:
        kw.update(tim_source=tim, tim_filename="synthetic-vela.tim")
    project, report = load_project(**kw)
    assert project is not None, report.errors
    return project


@pytest.mark.parametrize("vela_has_tim", [True, False])
def test_every_dataset_gets_error_bars_equal_to_its_own_dat_sigma_regardless_of_tim(vela_has_tim):
    """Reported case: one complete dataset (PAR+DAT+TIM) and one PAR+DAT only."""
    vela = _vela(vela_has_tim)
    nicer = _project(with_tim=not vela_has_tim)
    projects = [vela, nicer]
    results = {**_compute(vela), **_compute(nicer)}
    fig = _fig()
    P.plot_residuals(fig, projects, results)
    for axis_idx, scale in ((0, 1.0), (1, 1e15)):
        containers = _errorbar_containers(fig.axes[axis_idx])
        assert len(containers) == 2
        for container, project in zip(containers, projects):
            assert container.has_yerr, "error bars missing for a dataset"
            sigma = (project.observations.f0_err if axis_idx == 0 else project.observations.f1_err) * scale
            np.testing.assert_allclose(_bar_half_lengths(container), sigma[np.isfinite(sigma)], rtol=1e-9)


def test_bars_are_never_inflated_even_when_subpixel():
    """Sub-pixel bars must still equal the DAT σ (honest), not be enlarged to be visible."""
    vela = _vela(True)
    fig = _fig()
    P.plot_residuals(fig, [vela], _compute(vela))
    container = _errorbar_containers(fig.axes[0])[0]
    assert np.nanmedian(_bar_half_lengths(container)) == pytest.approx(np.nanmedian(vela.observations.f0_err), rel=1e-9)
