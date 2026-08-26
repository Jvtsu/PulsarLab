from __future__ import annotations

import os

import numpy as np
import pytest

from pulsarlab.datasets.loader import load_project
from pulsarlab.engine.pipeline import Pipeline
from pulsarlab.i18n.translator import Translator
from pulsarlab.visualization.matplotlib_plots import _display_indices


PAR = """
PSRJ JMERGE+0000
F0 10
F1 -1e-10
PEPOCH 58000
START 57999
FINISH 58010
GLEP_1 58005
GLF0_1 1e-6
"""

TIM = """FORMAT 1
toa0 1400 58004.0 2.0 @ -pn 10
toa1 1400 58005.0 3.0 @ -pn 11
toa2 1400 58006.0 4.0 @ -pn 12
"""


def _project():
    project, report = load_project(
        par_source=PAR,
        tim_source=TIM,
        par_filename="merge.par",
        tim_filename="merge.tim",
    )
    assert project is not None, report.errors
    return project


def test_pipeline_can_skip_expensive_toa_outputs_for_non_toa_views():
    project = _project()
    pipeline = Pipeline()

    lean = pipeline.compute(
        project,
        compute_toa_series=False,
        summarize_toas=False,
    )
    assert lean.toa_phase.size == 0
    assert lean.toa_frequency.size == 0
    assert lean.glitch_toa_summaries == ()

    full = pipeline.compute(project)
    assert full.toa_phase.size == 3
    assert full.toa_frequency.size == 3
    assert len(full.glitch_toa_summaries) == 1


def test_plot_display_indices_cap_rendering_without_losing_endpoints():
    indices = _display_indices(100_000)
    assert indices.size == 25_000
    assert indices[0] == 0
    assert indices[-1] == 99_999
    assert np.all(np.diff(indices) > 0)
    assert np.array_equal(_display_indices(10), np.arange(10))


def test_recovered_desktop_translations_exist_in_both_languages():
    keys = (
        "information.tooltip",
        "toolbar.home",
        "toolbar.save.tip",
        "legend.observed",
        "legend.no_glitches",
        "plot.glitches_toas.no_uncertainties",
        "dialog.filter_par",
    )
    for language in ("es", "en"):
        tr = Translator(language)
        for key in keys:
            assert tr.tr(key) != key


def test_information_tab_is_a_dedicated_desktop_view():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from pulsarlab.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.workspace.set_view("information")
    app.processEvents()

    button = window.workspace.information_button
    assert button.width() == 28
    assert button.height() == 28
    assert button.isChecked()
    assert window.workspace.information.isVisible() or not window.isVisible()
    assert not window.workspace.canvas.isVisible()
    window.close()
