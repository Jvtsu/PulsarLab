"""Qt-level regressions for issues reported on macOS (light system theme)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from matplotlib.backends.backend_qt import FigureCanvasQT, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from pulsarlab.ui.main_window import MainWindow
from pulsarlab.ui.navigation import ThemedNavigationToolbar
from pulsarlab.ui.theme import APP_QSS
from sample_data import write_sample_files



def _app_with_light_system_palette():
    """What macOS looks like in light mode: dark text on a light window."""
    app = QApplication.instance() or QApplication([])
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(236, 236, 236))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(236, 236, 236))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    app.setPalette(palette)
    app.setStyleSheet(APP_QSS)
    return app


def _icon_brightness(toolbar) -> list[float]:
    values = []
    for action in toolbar.actions():
        icon = action.icon()
        if icon.isNull():
            continue
        image = icon.pixmap(32, 32).toImage()
        total = count = 0.0
        for x in range(image.width()):
            for y in range(image.height()):
                color = image.pixelColor(x, y)
                if color.alpha() > 200:
                    total += color.lightnessF()
                    count += 1
        assert count > 0, action.text()
        values.append(total / count)
    return values


def test_toolbar_icons_are_light_even_when_the_system_theme_is_light():
    app = _app_with_light_system_palette()
    canvas = FigureCanvasQT(Figure())
    themed = ThemedNavigationToolbar(canvas, None)
    brightness = _icon_brightness(themed)
    assert len(brightness) >= 6
    assert min(brightness) > 0.6, brightness


def test_control_plain_matplotlib_toolbar_is_dark_on_light_system_theme():
    """Negative control: proves the test above detects the original bug."""
    app = _app_with_light_system_palette()
    canvas = FigureCanvasQT(Figure())
    plain = NavigationToolbar2QT(canvas, None)
    assert max(_icon_brightness(plain)) < 0.2


def _window(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window._show_message = lambda *args, **kwargs: None
    par_path, dat_path, tim_path = write_sample_files(tmp_path / "primary")
    window.load_project_paths(str(par_path), str(dat_path), str(tim_path) if tim_path else None)
    window.resize(1300, 800)
    window.show()
    app.processEvents()
    return app, window


def test_main_window_uses_themed_toolbar_and_errorbar_toggle_follows_view(tmp_path):
    app, window = _window(tmp_path)
    ws = window.workspace
    assert isinstance(ws.navbar, ThemedNavigationToolbar)
    for view, expected in (("spin_analysis", True), ("residuals", True), ("datasets", True), ("glitches_toas", False)):
        ws.set_view(view)
        app.processEvents()
        assert ws.errorbar_check.isHidden() is (not expected), view


def _containers(ax):
    return [c for c in ax.containers if hasattr(c, "has_yerr")]


def test_errorbar_checkbox_removes_bars_from_residuals(tmp_path):
    app, window = _window(tmp_path)
    ws = window.workspace
    ws.set_view("residuals")
    ws.refresh()
    assert _containers(ws.fig.axes[0])[0].has_yerr
    ws.errorbar_check.setChecked(False)
    ws.refresh()
    assert not _containers(ws.fig.axes[0])[0].has_yerr


def test_spin_delta_panels_in_window_include_observed_points_and_toggles(tmp_path):
    app, window = _window(tmp_path)
    ws = window.workspace
    for key in ("delta_f0", "delta_f1"):
        ws.spin_panel_buttons[key].setChecked(True)
    ws.set_view("spin_analysis")
    ws.refresh()
    delta_axes = [ax for ax in ws.fig.axes if ax.get_ylabel().startswith("ΔF")]
    assert len(delta_axes) == 2
    for ax in delta_axes:
        assert _containers(ax), ax.get_ylabel()
    # "F0 observed" checkbox also drives the ΔF0 observed points
    ws.line_checks["f0_obs"].setChecked(False)
    ws.refresh()
    ax0 = [ax for ax in ws.fig.axes if ax.get_ylabel().startswith("ΔF0")][0]
    assert not any(c.lines[0].get_visible() for c in _containers(ax0))
    # Observed/model checkboxes stay usable when only the ΔF panel is on
    ws.spin_panel_buttons["f0"].setChecked(False)
    ws._update_spin_line_control_state()
    assert ws.line_checks["f0_obs"].isEnabled()
    assert not ws.line_checks["f0_noglit"].isEnabled()


def test_information_tab_answers_the_reported_questions():
    from pulsarlab.i18n.translator import Translator
    for lang, needles in (
        ("en", ("TOA window", "Error bars", "no baseline", "not</b> the same quantity as the ΔF0")),
        ("es", ("Ventana TOA", "Barras de error", "ni línea base", "No</b> es la misma magnitud que el panel ΔF0")),
    ):
        text = Translator(lang).tr("information.html")
        for needle in needles:
            assert needle in text, (lang, needle)


def test_residual_summary_flags_datasets_whose_error_bars_are_subpixel(tmp_path):
    """The synthetic second dataset has σ far below its residual scatter."""
    app, window = _window(tmp_path)
    second_par, second_dat, _ = write_sample_files(
        tmp_path / "second", prefix="synthetic-second", psr="J0835-4510",
        f0=11.2, f1=-1.55e-11, f0_error=1.0e-13, noise_amplitude=1.0e-6, with_tim=False,
    )
    window.load_project_paths(str(second_par), str(second_dat), None)
    app.processEvents()
    ws = window.workspace
    ws.set_view("residuals")
    ws.refresh()
    lines = ws.info.toPlainText().split("\n")
    text = "\n".join(lines)
    assert text.count("Error bars (DAT σ") == 2, text      # reported for both datasets
    assert text.count("⚠") == 1, text                     # warning only for the sub-pixel one
    warned = [i for i, l in enumerate(lines) if "⚠" in l][0]
    assert "σ=1.00e-13" in lines[warned - 1], lines[warned - 1]   # the warning belongs to the synthetic second dataset
