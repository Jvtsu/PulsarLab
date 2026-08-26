"""Thin PySide6 interface for PulsarLab.

The UI assembles projects from independently loaded PAR/DAT/TIM files and only
renders arrays already computed by the UI-free engine.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import cast

import numpy as np

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget, QTextEdit, QCheckBox, QComboBox, QDoubleSpinBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from pulsarlab.datasets.loader import ComponentKind, attach_component, load_project
from pulsarlab.engine.pipeline import Pipeline, ProjectNotComputableError
from pulsarlab.i18n.dynamic_messages import localize_messages
from pulsarlab.i18n.translator import Translator
from pulsarlab.state.app_state import AppState
from pulsarlab.ui.theme import APP_QSS
from pulsarlab.visualization.range_tools import apply_mjd_range_to_figure, compute_visible_mjd_span, normalise_mjd_range
from pulsarlab.visualization.matplotlib_plots import (
    plot_dataset_summary,
    plot_glitches_toas,
    plot_residuals,
    plot_spin_analysis,
)


def _qt_button_text(text: str) -> str:
    """Show translation text literally on Qt buttons.

    Qt interprets a single ampersand as a mnemonic marker. Doubling it keeps
    labels such as "Glitches & TOAs" visible exactly as translated.
    """
    return str(text).replace("&", "&&")


class Navigator(QWidget):
    def __init__(self, state: AppState, on_change, on_add_file, tr: Translator) -> None:
        super().__init__()
        self.state = state
        self.on_change = on_change
        self.on_add_file = on_add_file
        self.translator = tr
        layout = QVBoxLayout(self)
        self.header = QLabel(self.translator.tr("navigator.title"))
        self.header.setObjectName("Header")
        layout.addWidget(self.header)

        self.active_pulsar = QLabel()
        self.active_pulsar.setObjectName("PulsarBadge")
        self.active_pulsar.setWordWrap(True)
        layout.addWidget(self.active_pulsar)

        add_row = QHBoxLayout()
        self.add_buttons: dict[str, QPushButton] = {}
        for kind in ("par", "dat", "tim"):
            button = QPushButton(_qt_button_text(self.translator.tr(f"button.add_{kind}")))
            button.clicked.connect(lambda _=False, k=kind: self.on_add_file(k))
            self.add_buttons[kind] = button
            add_row.addWidget(button)
        layout.addLayout(add_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._item_changed)
        self.tree.itemClicked.connect(self._item_clicked)
        layout.addWidget(self.tree, 1)
        self._update_active_pulsar_label()

    def retranslate(self) -> None:
        self.header.setText(self.translator.tr("navigator.title"))
        for kind, button in self.add_buttons.items():
            button.setText(_qt_button_text(self.translator.tr(f"button.add_{kind}")))
        self._update_active_pulsar_label()

    def _pulsar_label(self, project) -> str:
        if project is None or project.par is None:
            return self.translator.tr("datasets.unidentified")
        return project.pulsar_name

    def _update_active_pulsar_label(self) -> None:
        active = self.state.datasets.active()
        pulsar = self._pulsar_label(active) if active is not None else self.translator.tr("navigator.no_active_pulsar")
        self.active_pulsar.setText(f"{self.translator.tr('navigator.active_pulsar')}: {pulsar}")

    def refresh(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self._update_active_pulsar_label()
        for idx, project in enumerate(self.state.datasets.all(), start=1):
            kinds = "+".join(project.file_kinds) or self.translator.tr("datasets.empty")
            pulsar = self._pulsar_label(project)
            descriptor = pulsar if project.name.casefold() in pulsar.casefold() else f"{pulsar} · {project.name}"
            item = QTreeWidgetItem([f"P{idx} · {descriptor} [{kinds}]"])
            item.setData(0, Qt.ItemDataRole.UserRole, project.dataset_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(0, Qt.CheckState.Checked if project.visible else Qt.CheckState.Unchecked)
            tooltip = [pulsar, f"PAR: {'✓' if project.par else '—'}", f"DAT: {project.n_observations}", f"TIM: {project.n_toas}"]
            item.setToolTip(0, "\n".join(tooltip))
            self.tree.addTopLevelItem(item)
            if project.dataset_id == self.state.datasets.active_id:
                self.tree.setCurrentItem(item)
        self.tree.blockSignals(False)

    def _item_changed(self, item: QTreeWidgetItem | None, column: int) -> None:
        if item is None:
            return
        project_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not project_id:
            return
        visible = item.checkState(0) == Qt.CheckState.Checked
        QTimer.singleShot(0, lambda: self._apply_visibility(project_id, visible))

    def _apply_visibility(self, project_id: str, visible: bool) -> None:
        self.state.datasets.set_visible(project_id, visible)
        self.on_change()

    def _item_clicked(self, item: QTreeWidgetItem | None, column: int) -> None:
        if item is None:
            return
        project_id = item.data(0, Qt.ItemDataRole.UserRole)
        if project_id:
            self.state.datasets.active_id = project_id
            self.on_change(light=True)


class Workspace(QWidget):
    VIEWS = [
        ("spin_analysis", "workspace.spin_analysis"),
        ("glitches_toas", "workspace.glitches_toas"),
        ("residuals", "workspace.residuals"),
        ("datasets", "workspace.datasets"),
    ]

    def __init__(self, state: AppState, pipeline: Pipeline, tr: Translator, on_language_change=None) -> None:
        super().__init__()
        self.state = state
        self.pipeline = pipeline
        self.translator = tr
        self.on_language_change = on_language_change
        self._view = "spin_analysis"
        self._refresh_pending = False
        self._mjd_range_manual: tuple[float, float] | None = None
        self._mjd_widget_syncing = False
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for view, key in self.VIEWS:
            button = QPushButton(_qt_button_text(self.translator.tr(key)))
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, v=view: self.set_view(v))
            self.buttons[view] = button
            toolbar.addWidget(button)
        self.information_button = QPushButton("?")
        self.information_button.setObjectName("InformationTabButton")
        self.information_button.setCheckable(True)
        self.information_button.setFixedSize(28, 28)
        self.information_button.setToolTip(self.translator.tr("information.tooltip"))
        self.information_button.setAccessibleName(self.translator.tr("workspace.information"))
        self.information_button.clicked.connect(lambda _=False: self.set_view("information"))
        self.buttons["information"] = self.information_button
        toolbar.addWidget(self.information_button)
        toolbar.addStretch(1)
        self.language_label = QLabel(self.translator.tr("settings.language"))
        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("Español", "es")
        self.language.setCurrentIndex(1 if self.state.language == "es" else 0)
        self.language.currentIndexChanged.connect(self._language_changed)
        toolbar.addWidget(self.language_label)
        toolbar.addWidget(self.language)
        layout.addLayout(toolbar)

        self.spin_graph_controls = QWidget()
        graph_controls = QHBoxLayout(self.spin_graph_controls)
        graph_controls.setContentsMargins(0, 0, 0, 0)
        self.graphs_label = QLabel(self.translator.tr("graphs.visible"))
        graph_controls.addWidget(self.graphs_label)
        self.spin_panel_buttons: dict[str, QPushButton] = {}
        panel_options = [
            ("f0", "graphs.f0", True),
            ("f1", "graphs.f1", True),
            ("phase", "graphs.phase", False),
            ("delta_f0", "graphs.delta_f0", False),
            ("delta_f1", "graphs.delta_f1", False),
        ]
        for key, label_key, checked in panel_options:
            button = QPushButton(_qt_button_text(self.translator.tr(label_key)))
            button.setCheckable(True)
            button.setChecked(checked)
            button.setToolTip(self.translator.tr("graphs.toggle_hint"))
            button.clicked.connect(lambda state=False, k=key: self._spin_panel_toggled(k, state))
            self.spin_panel_buttons[key] = button
            graph_controls.addWidget(button)
        graph_controls.addStretch(1)
        layout.addWidget(self.spin_graph_controls)

        self.line_controls = QWidget()
        controls = QHBoxLayout(self.line_controls)
        controls.setContentsMargins(0, 0, 0, 0)
        self.visible_label = QLabel(self.translator.tr("lines.visible"))
        controls.addWidget(self.visible_label)
        self.line_checks: dict[str, QCheckBox] = {}
        line_options = [
            ("f0_obs", "lines.f0_obs"), ("f0_model", "lines.f0_model"),
            ("f0_noglit", "lines.f0_noglit"), ("f1_obs", "lines.f1_obs"),
            ("f1_model", "lines.f1_model"), ("f1_noglit", "lines.f1_noglit"),
            ("glitches", "lines.glitches"),
        ]
        for key, label_key in line_options:
            checkbox = QCheckBox(self.translator.tr(label_key))
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(lambda _=0: self.schedule_refresh())
            self.line_checks[key] = checkbox
            controls.addWidget(checkbox)
        controls.addStretch(1)
        layout.addWidget(self.line_controls)

        self.analysis_controls = QWidget()
        analysis_layout = QHBoxLayout(self.analysis_controls)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        self.toa_window_label = QLabel(self.translator.tr("toa.window"))
        self.toa_window = QDoubleSpinBox()
        self.toa_window.setRange(0.01, 10000.0)
        self.toa_window.setDecimals(2)
        self.toa_window.setValue(30.0)
        self.toa_window.setSuffix(" d")
        self.toa_window.setKeyboardTracking(False)
        self.toa_window.valueChanged.connect(lambda _=0.0: self.schedule_refresh())
        analysis_layout.addWidget(self.toa_window_label)
        analysis_layout.addWidget(self.toa_window)
        analysis_layout.addStretch(1)
        layout.addWidget(self.analysis_controls)

        self.mjd_controls = QWidget()
        mjd_layout = QHBoxLayout(self.mjd_controls)
        mjd_layout.setContentsMargins(0, 0, 0, 0)
        self.mjd_label = QLabel(self.translator.tr("mjd.range"))
        self.mjd_min_label = QLabel(self.translator.tr("mjd.from"))
        self.mjd_max_label = QLabel(self.translator.tr("mjd.to"))
        self.mjd_min = QDoubleSpinBox()
        self.mjd_max = QDoubleSpinBox()
        for box in (self.mjd_min, self.mjd_max):
            box.setDecimals(6)
            box.setRange(-1_000_000_000.0, 1_000_000_000.0)
            box.setSingleStep(1.0)
            box.setKeyboardTracking(False)
            box.setMinimumWidth(130)
            box.valueChanged.connect(lambda _=0.0: self._mjd_values_changed())
        self.mjd_apply = QPushButton(_qt_button_text(self.translator.tr("mjd.apply")))
        self.mjd_auto = QPushButton(_qt_button_text(self.translator.tr("mjd.auto")))
        self.mjd_apply.clicked.connect(self._apply_mjd_range)
        self.mjd_auto.clicked.connect(self._auto_mjd_range)
        for widget in (self.mjd_label, self.mjd_min_label, self.mjd_min, self.mjd_max_label, self.mjd_max, self.mjd_apply, self.mjd_auto):
            mjd_layout.addWidget(widget)
        mjd_layout.addStretch(1)
        layout.addWidget(self.mjd_controls)

        self.fig = Figure(figsize=(9, 7), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("pick_event", self._on_pick)
        self.navbar = NavigationToolbar(self.canvas, self)
        self._retranslate_navigation_toolbar()
        layout.addWidget(self.navbar)
        layout.addWidget(self.canvas, 1)
        self.information = QTextEdit()
        self.information.setReadOnly(True)
        self.information.setHtml(self.translator.tr("information.html"))
        self.information.setVisible(False)
        layout.addWidget(self.information, 1)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(180)
        layout.addWidget(self.info)
        self.set_view("spin_analysis")

    def retranslate(self) -> None:
        for view, key in self.VIEWS:
            self.buttons[view].setText(_qt_button_text(self.translator.tr(key)))
        self.information_button.setToolTip(self.translator.tr("information.tooltip"))
        self.information_button.setAccessibleName(self.translator.tr("workspace.information"))
        self.information.setHtml(self.translator.tr("information.html"))
        self.language_label.setText(self.translator.tr("settings.language"))
        self.graphs_label.setText(self.translator.tr("graphs.visible"))
        for key, label_key in [
            ("f0", "graphs.f0"), ("f1", "graphs.f1"),
            ("phase", "graphs.phase"), ("delta_f0", "graphs.delta_f0"),
            ("delta_f1", "graphs.delta_f1"),
        ]:
            self.spin_panel_buttons[key].setText(self.translator.tr(label_key))
            self.spin_panel_buttons[key].setToolTip(self.translator.tr("graphs.toggle_hint"))
        self.visible_label.setText(self.translator.tr("lines.visible"))
        for key, label_key in [
            ("f0_obs", "lines.f0_obs"), ("f0_model", "lines.f0_model"),
            ("f0_noglit", "lines.f0_noglit"), ("f1_obs", "lines.f1_obs"),
            ("f1_model", "lines.f1_model"), ("f1_noglit", "lines.f1_noglit"),
            ("glitches", "lines.glitches"),
        ]:
            self.line_checks[key].setText(self.translator.tr(label_key))
        self.toa_window_label.setText(self.translator.tr("toa.window"))
        self.mjd_label.setText(self.translator.tr("mjd.range"))
        self.mjd_min_label.setText(self.translator.tr("mjd.from"))
        self.mjd_max_label.setText(self.translator.tr("mjd.to"))
        self.mjd_apply.setText(_qt_button_text(self.translator.tr("mjd.apply")))
        self.mjd_auto.setText(_qt_button_text(self.translator.tr("mjd.auto")))
        self._retranslate_navigation_toolbar()

    def _retranslate_navigation_toolbar(self) -> None:
        key_by_english = {
            "home": "home", "back": "back", "forward": "forward", "pan": "pan",
            "zoom": "zoom", "subplots": "subplots", "customize": "customize", "save": "save",
        }
        for action in self.navbar.actions():
            key = getattr(action, "_pulsarlab_translation_key", None)
            if key is None:
                raw = action.text().replace("&", "").strip().casefold()
                key = key_by_english.get(raw)
                if key is not None:
                    setattr(action, "_pulsarlab_translation_key", key)
            if key is None:
                continue
            action.setText(self.translator.tr(f"toolbar.{key}"))
            tip = self.translator.tr(f"toolbar.{key}.tip")
            action.setToolTip(tip)
            action.setStatusTip(tip)

    def _language_changed(self) -> None:
        language = self.language.currentData()
        self.translator.set_language(language)
        self.state.language = language
        self.retranslate()
        if self.on_language_change is not None:
            self.on_language_change()
        self.refresh()

    def set_view(self, view: str) -> None:
        self._view = view
        self.state.current_view = view
        for name, button in self.buttons.items():
            button.setChecked(name == view)
        is_information = view == "information"
        is_spin = view == "spin_analysis"
        self.spin_graph_controls.setVisible(is_spin)
        self.line_controls.setVisible(is_spin)
        self.analysis_controls.setVisible(view == "glitches_toas")
        self.mjd_controls.setVisible(not is_information)
        self.navbar.setVisible(not is_information)
        self.canvas.setVisible(not is_information)
        self.info.setVisible(not is_information)
        self.information.setVisible(is_information)
        self._update_spin_line_control_state()
        self.refresh()

    def _spin_panel_toggled(self, key: str, checked: bool) -> None:
        if not checked and not any(button.isChecked() for button in self.spin_panel_buttons.values()):
            self.spin_panel_buttons[key].setChecked(True)
            return
        self._update_spin_line_control_state()
        self.schedule_refresh()

    def _spin_panels(self) -> dict[str, bool]:
        return {key: button.isChecked() for key, button in self.spin_panel_buttons.items()}

    def _update_spin_line_control_state(self) -> None:
        f0_enabled = self.spin_panel_buttons["f0"].isChecked()
        f1_enabled = self.spin_panel_buttons["f1"].isChecked()
        for key in ("f0_obs", "f0_model", "f0_noglit"):
            self.line_checks[key].setEnabled(f0_enabled)
        for key in ("f1_obs", "f1_model", "f1_noglit"):
            self.line_checks[key].setEnabled(f1_enabled)
        self.line_checks["glitches"].setEnabled(any(self._spin_panels().values()))

    def _mjd_values_changed(self) -> None:
        if self._mjd_widget_syncing:
            return

    def _apply_mjd_range(self) -> None:
        auto_span = compute_visible_mjd_span(self.state.datasets.visible())
        self._mjd_range_manual = normalise_mjd_range(self.mjd_min.value(), self.mjd_max.value(), auto_span)
        self.refresh()

    def _auto_mjd_range(self) -> None:
        self._mjd_range_manual = None
        self.refresh()

    def _sync_mjd_widgets(self, projects) -> tuple[float, float] | None:
        auto_span = compute_visible_mjd_span(projects)
        active_span = self._mjd_range_manual or auto_span
        self._mjd_widget_syncing = True
        try:
            enabled = active_span is not None
            for widget in (self.mjd_min, self.mjd_max, self.mjd_apply):
                widget.setEnabled(enabled)
            self.mjd_auto.setEnabled(enabled and self._mjd_range_manual is not None)
            if active_span is not None:
                self.mjd_min.setValue(float(active_span[0]))
                self.mjd_max.setValue(float(active_span[1]))
        finally:
            self._mjd_widget_syncing = False
        return active_span

    def schedule_refresh(self) -> None:
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(35, self.refresh)

    def _plot_labels(self) -> dict[str, str]:
        return {
            "spin_analysis.title": self.translator.tr("plot.spin_analysis.title"),
            "phase.ylabel": self.translator.tr("plot.phase.ylabel"),
            "phase.load_par": self.translator.tr("plot.phase.load_par"),
            "glitches_toas.title": self.translator.tr("plot.glitches_toas.title"),
            "glitches_toas.timeline": self.translator.tr("plot.glitches_toas.timeline"),
            "glitches_toas.error": self.translator.tr("plot.glitches_toas.error"),
            "glitches_toas.no_toas": self.translator.tr("plot.glitches_toas.no_toas"),
            "glitches_toas.no_uncertainties": self.translator.tr("plot.glitches_toas.no_uncertainties"),
            "residuals.title": self.translator.tr("plot.residuals.title"),
            "residuals.no_dat": self.translator.tr("plot.residuals.no_dat"),
            "datasets.title": self.translator.tr("plot.datasets.title"),
            "legend.observed": self.translator.tr("legend.observed"),
            "legend.model": self.translator.tr("legend.model"),
            "legend.no_glitches": self.translator.tr("legend.no_glitches"),
            "legend.phase": self.translator.tr("legend.phase"),
            "legend.glitch": self.translator.tr("legend.glitch"),
            "legend.residual": self.translator.tr("legend.residual"),
        }

    def _visibility(self, projects) -> dict[str, bool]:
        visibility = {"glitches": self.line_checks["glitches"].isChecked()}
        computed = [project for project in projects if project.par is not None]
        for idx, _project in enumerate(computed, start=1):
            visibility[f"D{idx} F0 obs"] = self.line_checks["f0_obs"].isChecked()
            visibility[f"D{idx} F0 model"] = self.line_checks["f0_model"].isChecked()
            visibility[f"D{idx} F0 no glitches"] = self.line_checks["f0_noglit"].isChecked()
            visibility[f"D{idx} F1 obs"] = self.line_checks["f1_obs"].isChecked()
            visibility[f"D{idx} F1 model"] = self.line_checks["f1_model"].isChecked()
            visibility[f"D{idx} F1 no glitches"] = self.line_checks["f1_noglit"].isChecked()
        return visibility

    def refresh(self) -> None:
        self._refresh_pending = False
        if self._view == "information":
            self.information.setHtml(self.translator.tr("information.html"))
            return
        projects = self.state.datasets.visible()
        if not projects:
            self._sync_mjd_widgets([])
            self.fig.clear()
            ax = self.fig.subplots(1, 1)
            ax.set_facecolor("#0B1020")
            self.fig.patch.set_facecolor("#070B14")
            ax.text(0.5, 0.5, self.translator.tr("alert.no_data"), ha="center", va="center", color="#E9F1FF", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            self.info.setPlainText("")
            self.canvas.draw_idle()
            return

        results = {}
        for project in projects:
            if project.par is None:
                continue
            try:
                results[project.dataset_id] = self.pipeline.compute(
                    project,
                    include_glitches=self.state.include_glitches,
                    toa_window_days=self.toa_window.value(),
                    compute_toa_series=False,
                    summarize_toas=self._view == "glitches_toas",
                )
            except ProjectNotComputableError:
                continue

        labels = self._plot_labels()
        active_mjd_range = self._sync_mjd_widgets(projects)
        if self._view == "spin_analysis":
            plot_spin_analysis(
                self.fig,
                projects,
                results,
                visibility=self._visibility(projects),
                labels=labels,
                panels=self._spin_panels(),
            )
            self.info.setPlainText(self._spin_summary(projects, results))
        elif self._view == "glitches_toas":
            plot_glitches_toas(self.fig, projects, results, labels=labels, toa_window=self.toa_window.value())
            self.info.setPlainText(self._glitch_toa_summary(projects, results))
        elif self._view == "residuals":
            plot_residuals(self.fig, projects, results, labels=labels)
            self.info.setPlainText(self._residual_summary(projects, results))
        else:
            plot_dataset_summary(self.fig, projects, results, labels=labels)
            self.info.setPlainText(self._project_summary(projects, results))
        apply_mjd_range_to_figure(self.fig, active_mjd_range)
        self.canvas.draw_idle()

    def _on_pick(self, event) -> None:
        artist = getattr(event, "artist", None)
        group = getattr(artist, "_pulsarlab_glitch_group", None)
        project_id = getattr(artist, "_pulsarlab_dataset_id", None)
        if group is None or project_id is None:
            return
        project = self.state.datasets.get(project_id)
        if project is None:
            return
        lines = [f"{project.name} · {group.get('label', 'G')} · MJD={group.get('glep')}"]
        for component in group.get("components", []):
            gltd = "—" if component.gltd is None else f"{component.gltd:g} d"
            lines.append(
                f"G{component.index}: GLPH={component.glph:.3e}, GLF0={component.glf0:.3e}, "
                f"GLF1={component.glf1:.3e}, GLF2={component.glf2:.3e}, GLF0D={component.glf0d:.3e}, GLTD={gltd}"
            )

        glep = group.get("glep")
        if glep is not None and project.toas is not None:
            indices = project.toas.near_mjd(float(glep), self.toa_window.value())
            lines.append("")
            lines.append(f"{self.translator.tr('glitches_toas.nearby')} (±{self.toa_window.value():g} d): {indices.size}")
            if indices.size == 0:
                lines.append(self.translator.tr("glitches_toas.none_nearby"))
            else:
                delta = project.toas.mjd[indices] - float(glep)
                order = indices[np.argsort(np.abs(delta))]
                lines.append(self.translator.tr("glitches_toas.columns"))
                for toa_index in order[:25]:
                    toa = project.toas.row(int(toa_index))
                    sigma = "—" if not np.isfinite(toa.uncertainty_us) else f"{toa.uncertainty_us:.3g}"
                    pulse = "—" if toa.pulse_number is None else f"{toa.pulse_number:g}"
                    lines.append(
                        f"{toa.name} | {toa.mjd:.12f} | {toa.mjd - float(glep):+.6f} | {sigma} | "
                        f"{toa.observatory or '—'} | {pulse}"
                    )
                remaining = int(indices.size - min(indices.size, 25))
                if remaining > 0:
                    lines.append(f"… {remaining} {self.translator.tr('glitches_toas.more')}")
        self.info.setPlainText("\n".join(lines))

    def _spin_summary(self, projects, results) -> str:
        active_labels = [button.text() for button in self.spin_panel_buttons.values() if button.isChecked()]
        lines = [
            self.translator.tr("spin_analysis.info"),
            f"{self.translator.tr('spin_analysis.visible_panels')}: {', '.join(active_labels)}",
        ]
        for idx, project in enumerate(projects, start=1):
            result = results.get(project.dataset_id)
            if result is None:
                lines.append(f"P{idx} {project.name}: {self.translator.tr('project.no_par')}")
            elif project.observations is None:
                lines.append(f"P{idx} {project.name}: {self.translator.tr('summary.model_grid')}={result.model_mjd.size}, {self.translator.tr('project.no_dat')}")
            else:
                lines.append(f"P{idx} {project.name}: F0 RMS={result.stats_f0.rms:.3e}, {self.translator.tr('summary.mean')}={result.stats_f0.mean:.3e}, n={result.stats_f0.n}")
        return "\n".join(lines)

    def _residual_summary(self, projects, results) -> str:
        lines = []
        for idx, project in enumerate(projects, start=1):
            result = results.get(project.dataset_id)
            if result is None or project.observations is None:
                lines.append(f"P{idx} {project.name}: {self.translator.tr('project.needs_par_dat')}")
                continue
            chi = "—" if result.stats_f0.chi2_red is None else f"{result.stats_f0.chi2_red:.3f}"
            lines.append(f"P{idx} {project.name}: F0 rms={result.stats_f0.rms:.3e}, χ²red={chi}, n={result.stats_f0.n}")
        return "\n".join(lines)

    def _glitch_toa_summary(self, projects, results) -> str:
        lines = [
            f"{self.translator.tr('glitches_toas.window')}: ±{self.toa_window.value():g} d",
            " | ".join([
                self.translator.tr("summary.glitch"), "MJD", "TOAs",
                self.translator.tr("summary.before_after"), self.translator.tr("summary.nearest_delta"),
                self.translator.tr("summary.median_sigma"), self.translator.tr("summary.coverage"),
            ]),
        ]
        for idx, project in enumerate(projects, start=1):
            result = results.get(project.dataset_id)
            if result is None:
                lines.append(f"P{idx} {project.name}: {self.translator.tr('project.no_par')}")
                continue
            if not result.glitch_toa_summaries:
                lines.append(f"P{idx} {project.name}: {self.translator.tr('project.no_glitches')}")
                continue
            for summary in result.glitch_toa_summaries:
                nearest = "—" if summary.nearest_delta_days is None else f"{summary.nearest_delta_days:+.4f}"
                sigma = "—" if summary.median_uncertainty_us is None else f"{summary.median_uncertainty_us:.3g}"
                balance = min(summary.before_count, summary.after_count) / max(summary.toa_count, 1)
                coverage_key = "coverage.good" if summary.toa_count >= 10 and balance >= 0.25 else ("coverage.limited" if summary.toa_count >= 5 else "coverage.poor")
                coverage = self.translator.tr(coverage_key)
                lines.append(
                    f"P{idx} {summary.label} | {summary.glep:.6f} | {summary.toa_count} | "
                    f"{summary.before_count}/{summary.after_count} | {nearest} | {sigma} | {coverage}"
                )
        return "\n".join(lines)

    def _project_summary(self, projects, results) -> str:
        lines = []
        for idx, project in enumerate(projects, start=1):
            lines.append(f"P{idx}: {project.name}")
            pulsar = project.pulsar_name if project.par is not None else self.translator.tr("datasets.unidentified")
            lines.append(f"  {self.translator.tr('datasets.pulsar')}: {pulsar}")
            lines.append(f"  {self.translator.tr('summary.files')}: {', '.join(project.file_kinds) or '—'}")
            lines.append(f"  {self.translator.tr('datasets.observations')}: {project.n_observations}")
            lines.append(f"  TOAs: {project.n_toas}")
            if project.par is not None:
                lines.append(f"  {self.translator.tr('datasets.glitch_components')}: {len(project.par.glitches)}")
            span = project.mjd_span
            if all(value == value for value in span):
                lines.append(f"  MJD: {span[0]:.6f} {self.translator.tr('summary.to')} {span[1]:.6f}")
            lines.append("")
        return "\n".join(lines).rstrip()


class MainWindow(QMainWindow):
    def __init__(self, initial_par: str | None = None, initial_dat: str | None = None, initial_tim: str | None = None) -> None:
        super().__init__()
        self.state = AppState()
        self.pipeline = Pipeline()
        self.translator = Translator(self.state.language)
        self.setWindowTitle(self.translator.tr("app.title"))
        self.resize(1440, 900)
        self._build_menu()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.navigator = Navigator(self.state, self._projects_changed, self.open_component_dialog, self.translator)
        self.workspace = Workspace(self.state, self.pipeline, self.translator, on_language_change=self._language_changed)
        splitter.addWidget(self.navigator)
        splitter.addWidget(self.workspace)
        splitter.setSizes([330, 1110])
        self.setCentralWidget(splitter)
        if initial_par or initial_dat or initial_tim:
            self.load_project_paths(initial_par, initial_dat, initial_tim)

    def _build_menu(self) -> None:
        self.menuBar().clear()
        file_menu = self.menuBar().addMenu(self.translator.tr("menu.file"))
        for raw_kind in ("par", "dat", "tim"):
            kind = cast(ComponentKind, raw_kind)
            action = file_menu.addAction(self.translator.tr(f"menu.add_{kind}"))
            action.triggered.connect(lambda _=False, k=kind: self.open_component_dialog(cast(ComponentKind, k)))
        file_menu.addSeparator()
        exit_action = file_menu.addAction(self.translator.tr("menu.exit"))
        exit_action.triggered.connect(self.close)

    def _language_changed(self) -> None:
        self.setWindowTitle(self.translator.tr("app.title"))
        self._build_menu()
        self.navigator.retranslate()
        self.navigator.refresh()

    def open_component_dialog(self, kind: ComponentKind) -> None:
        filters = {
            "par": self.translator.tr("dialog.filter_par"),
            "dat": self.translator.tr("dialog.filter_dat"),
            "tim": self.translator.tr("dialog.filter_tim"),
        }
        path, _ = QFileDialog.getOpenFileName(self, self.translator.tr(f"dialog.open_{kind}"), "", filters[kind])
        if path:
            self.load_component(kind, path)

    def _show_message(self, level: str, title: str, body: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical if level == "error" else QMessageBox.Icon.Information)
        box.setWindowTitle(title)
        box.setText(body)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok = box.button(QMessageBox.StandardButton.Ok)
        if ok is not None and self.state.language == "es":
            ok.setText("Aceptar")
        box.exec()

    def _active_attach_target(self, kind: ComponentKind):
        project = self.state.datasets.active()
        if project is None:
            return None
        if kind == "par" and project.par is None:
            return project
        if kind == "dat" and project.observations is None:
            return project
        if kind == "tim" and project.toas is None:
            return project
        return None

    def load_component(self, kind: ComponentKind, path: str) -> None:
        file_path = Path(path)
        target = self._active_attach_target(kind)
        if target is not None:
            project, report = attach_component(target, kind, file_path, file_path.name)
            if project is not None:
                self.state.datasets.replace_dataset(project)
        else:
            kwargs = {f"{kind}_source": file_path, f"{kind}_filename": file_path.name}
            project, report = load_project(**kwargs)
            if project is not None:
                self.state.datasets.add(project)
        self._finish_load(project, report)

    def load_project_paths(self, par_path: str | None, dat_path: str | None, tim_path: str | None) -> None:
        kwargs = {}
        for kind, path in (("par", par_path), ("dat", dat_path), ("tim", tim_path)):
            if path:
                file_path = Path(path)
                kwargs[f"{kind}_source"] = file_path
                kwargs[f"{kind}_filename"] = file_path.name
        project, report = load_project(**kwargs)
        if project is not None:
            self.state.datasets.add(project)
        self._finish_load(project, report)

    def _finish_load(self, project, report) -> None:
        language = self.state.language
        if project is None:
            messages = localize_messages(report.errors + report.warnings, language)
            self._show_message("error", self.translator.tr("alert.load_error"), "\n".join(messages))
            return
        self.pipeline.cache.clear()
        self.navigator.refresh()
        self.workspace.refresh()
        yes = self.translator.tr("summary.yes")
        no = self.translator.tr("summary.no")
        msg = (
            f"{self.translator.tr('alert.loaded_prefix')} '{project.name}'\n"
            f"PAR={yes if project.par else no}, DAT={project.n_observations}, TIM={project.n_toas}"
        )
        if report.warnings:
            warnings = localize_messages(report.warnings[:10], language)
            msg += "\n\n" + "\n".join("• " + warning for warning in warnings)
        self._show_message("info", self.translator.tr("alert.load_success"), msg)

    def _projects_changed(self, light: bool = False) -> None:
        self.navigator.refresh()
        self.workspace.refresh() if light else self.workspace.schedule_refresh()


def run_app(initial_par: str | None = None, initial_dat: str | None = None, initial_tim: str | None = None) -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    elif not isinstance(app, QApplication):
        raise RuntimeError("A non-GUI Qt application is already running.")
    app.setStyleSheet(APP_QSS)
    window = MainWindow(initial_par, initial_dat, initial_tim)
    window.show()
    return int(app.exec())
