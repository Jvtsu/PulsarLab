# pyright: reportGeneralTypeIssues=false
"""Optional PyQtGraph spin-evolution backend.

This module is intentionally optional.  It offers a fast interactive renderer for
large spin-evolution datasets while Matplotlib remains the publication/export
backend.  Importing this file without pyqtgraph installed raises a clear error;
PulsarLab's main app can fall back to Matplotlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pulsarlab.core.units import F1_DISPLAY_SCALE
from pulsarlab.visualization import theme as T

try:  # pragma: no cover - optional GUI backend
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtCore
    from PySide6.QtWidgets import QVBoxLayout, QWidget
except Exception as exc:  # pragma: no cover - optional GUI backend
    pg = None
    QWidget = object  # type: ignore
    QVBoxLayout = None  # type: ignore
    QtCore = None  # type: ignore
    _IMPORT_ERROR = exc
else:  # pragma: no cover
    _IMPORT_ERROR = None


@dataclass
class PyQtGraphBackendStatus:
    available: bool
    message: str


def backend_status() -> PyQtGraphBackendStatus:
    if pg is None:
        return PyQtGraphBackendStatus(False, f"PyQtGraph backend unavailable: {_IMPORT_ERROR}")
    return PyQtGraphBackendStatus(True, "PyQtGraph backend available.")


class PyQtGraphSpinWidget(QWidget):  # pragma: no cover - requires Qt session
    """Fast spin view for F0/F1, kept separate from the Matplotlib canvas."""

    def __init__(self, parent=None) -> None:
        if pg is None:
            raise RuntimeError(f"PyQtGraph backend unavailable: {_IMPORT_ERROR}")
        super().__init__(parent)
        pg.setConfigOptions(antialias=False, background=T.BG, foreground=T.TEXT)
        self._items: dict[str, Any] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.f0_plot = pg.PlotWidget(title="F0(t)")
        self.f1_plot = pg.PlotWidget(title="F1(t)")
        for plot in (self.f0_plot, self.f1_plot):
            plot.showGrid(x=True, y=True, alpha=0.25)
            plot.getAxis("bottom").setPen(pg.mkPen(T.MUTED))
            plot.getAxis("left").setPen(pg.mkPen(T.MUTED))
            plot.getAxis("bottom").setTextPen(pg.mkPen(T.MUTED))
            plot.getAxis("left").setTextPen(pg.mkPen(T.MUTED))
            plot.addLegend(offset=(10, 10))
        self.f0_plot.setLabel("bottom", "MJD")
        self.f0_plot.setLabel("left", "F0", units="Hz")
        self.f1_plot.setLabel("bottom", "MJD")
        self.f1_plot.setLabel("left", "F1", units="10^-15 Hz/s")
        layout.addWidget(self.f0_plot, 1)
        layout.addWidget(self.f1_plot, 1)

    def clear(self) -> None:
        self.f0_plot.clear()
        self.f1_plot.clear()
        self._items.clear()

    def update_spin(self, datasets, results, visibility: dict[str, bool] | None = None) -> None:
        visibility = visibility or {}
        self.clear()
        for idx, ds in enumerate(datasets, 1):
            res = results.get(ds.dataset_id)
            if res is None:
                continue
            color = T.DATASET_COLORS[(idx - 1) % len(T.DATASET_COLORS)]
            if ds.observations is not None and visibility.get(f"D{idx} F0 obs", True):
                self.f0_plot.plot(ds.observations.mjd, ds.observations.f0, pen=None, symbol="o", symbolSize=4, symbolBrush=color, name=f"D{idx} F0 obs")
            if visibility.get(f"D{idx} F0 model", True):
                self.f0_plot.plot(res.model_mjd, res.f0_model, pen=pg.mkPen(T.MODEL, width=2), name=f"D{idx} F0 model")
            if visibility.get(f"D{idx} F0 no glitches", True):
                self.f0_plot.plot(res.model_mjd, res.f0_noglit, pen=pg.mkPen(T.MUTED, width=1, style=QtCore.Qt.PenStyle.DotLine), name=f"D{idx} F0 no glitches")
            if ds.observations is not None and ds.observations.f1 is not None and visibility.get(f"D{idx} F1 obs", True):
                self.f1_plot.plot(ds.observations.mjd, ds.observations.f1 / F1_DISPLAY_SCALE, pen=None, symbol="o", symbolSize=4, symbolBrush=color, name=f"D{idx} F1 obs")
            if visibility.get(f"D{idx} F1 model", True):
                self.f1_plot.plot(res.model_mjd, res.f1_model / F1_DISPLAY_SCALE, pen=pg.mkPen(T.F1, width=2), name=f"D{idx} F1 model")
            if visibility.get(f"D{idx} F1 no glitches", True):
                self.f1_plot.plot(res.model_mjd, res.f1_noglit / F1_DISPLAY_SCALE, pen=pg.mkPen(T.MUTED, width=1, style=QtCore.Qt.PenStyle.DotLine), name=f"D{idx} F1 no glitches")
            if visibility.get("glitches", True):
                for group in res.glitch_groups:
                    glep = group.get("glep")
                    if glep is None:
                        continue
                    for plot in (self.f0_plot, self.f1_plot):
                        line = pg.InfiniteLine(float(glep), angle=90, movable=False, pen=pg.mkPen(T.GLITCH, width=1, style=QtCore.Qt.PenStyle.DotLine))
                        plot.addItem(line)
