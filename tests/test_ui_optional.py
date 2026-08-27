from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from pulsarlab.ui.main_window import MainWindow


PAR = """
PSRJ J0537-6910
F0 62
F1 -2e-10
PEPOCH 58000
START 58000
FINISH 58010
"""


def test_navigator_and_spin_graph_controls(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window._show_message = lambda *args, **kwargs: None

    par_path = tmp_path / "j0537.par"
    par_path.write_text(PAR)
    window.load_component("par", str(par_path))
    app.processEvents()

    assert "J0537-6910" in window.navigator.active_pulsar.text()
    assert "J0537-6910" in window.navigator.tree.topLevelItem(0).text(0)

    states = {key: button.isChecked() for key, button in window.workspace.spin_panel_buttons.items()}
    assert states == {
        "f0": True,
        "f1": True,
        "phase": False,
        "delta_f0": False,
        "delta_f1": False,
    }

    window.workspace.spin_panel_buttons["phase"].click()
    app.processEvents()
    assert window.workspace.spin_panel_buttons["phase"].isChecked()

    for button in window.workspace.spin_panel_buttons.values():
        button.setChecked(False)
    window.workspace._spin_panel_toggled("f0", False)
    assert window.workspace.spin_panel_buttons["f0"].isChecked()

    window.close()
