from __future__ import annotations

from matplotlib.figure import Figure

from pulsarlab.datasets.loader import load_project
from pulsarlab.engine.pipeline import Pipeline
from pulsarlab.visualization.matplotlib_plots import plot_spin_analysis


PAR = """
PSRJ J0537-6910
F0 62
F1 -2e-10
PEPOCH 58000
START 58000
FINISH 58010
GLEP_1 58005
GLF0_1 1e-6
"""
DAT = "58000 62 1e-9\n58005 61.9999 1e-9\n58010 61.9998 1e-9\n"


def _computed_project():
    project, report = load_project(par_source=PAR, dat_source=DAT, dataset_id="spin-panels")
    assert project is not None, report.errors
    return project, Pipeline().compute(project, grid_points=128)


def test_spin_analysis_can_show_only_core_spin_graphs():
    project, result = _computed_project()
    fig = Figure()
    plot_spin_analysis(
        fig,
        [project],
        {project.dataset_id: result},
        panels={"f0": True, "f1": True, "phase": False, "delta_f0": False, "delta_f1": False},
    )
    assert len(fig.axes) == 2
    assert [axis.get_ylabel() for axis in fig.axes] == ["F0 [Hz]", "F1 [10^-15 Hz/s]"]


def test_spin_analysis_can_show_one_diagnostic_graph():
    project, result = _computed_project()
    fig = Figure()
    plot_spin_analysis(
        fig,
        [project],
        {project.dataset_id: result},
        panels={"f0": False, "f1": False, "phase": True, "delta_f0": False, "delta_f1": False},
    )
    assert len(fig.axes) == 1
    assert fig.axes[0].get_ylabel() == "Phase [cycles]"
    assert fig.axes[0].get_xlabel() == "MJD"


def test_spin_analysis_default_keeps_api_compatibility():
    project, result = _computed_project()
    fig = Figure()
    plot_spin_analysis(fig, [project], {project.dataset_id: result})
    assert len(fig.axes) == 5


def test_spin_analysis_never_renders_an_empty_figure():
    project, result = _computed_project()
    fig = Figure()
    plot_spin_analysis(
        fig,
        [project],
        {project.dataset_id: result},
        panels={"f0": False, "f1": False, "phase": False, "delta_f0": False, "delta_f1": False},
    )
    assert len(fig.axes) == 1
    assert fig.axes[0].get_ylabel() == "F0 [Hz]"
