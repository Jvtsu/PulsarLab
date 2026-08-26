from __future__ import annotations

import pytest


def test_pyqtgraph_backend_status_is_clear():
    from pulsarlab.ui.pyqtgraph_spin import backend_status

    status = backend_status()
    assert isinstance(status.available, bool)
    assert status.message


def test_pyqtgraph_backend_imports_when_dependency_present():
    pytest.importorskip("pyqtgraph")
    from pulsarlab.ui.pyqtgraph_spin import PyQtGraphSpinWidget
    assert PyQtGraphSpinWidget is not None
