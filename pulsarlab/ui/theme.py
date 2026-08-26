"""Qt styles for PulsarLab."""

APP_QSS = """
QMainWindow, QWidget { background: #070B14; color: #E9F1FF; font-family: 'Segoe UI'; font-size: 10pt; }
QTreeWidget, QTextEdit, QComboBox, QDoubleSpinBox { background: #0B1020; color: #E9F1FF; border: 1px solid #263143; border-radius: 6px; }
QPushButton { background: #111A2E; color: #E9F1FF; border: 1px solid #263143; border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { border-color: #00D8FF; }
QPushButton:checked { background: #123247; border-color: #00D8FF; color: #00D8FF; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; }
QCheckBox::indicator:unchecked { border: 1px solid #53627A; background: #0B1020; }
QCheckBox::indicator:checked { border: 1px solid #00D8FF; background: #00D8FF; }
QTreeWidget::item:selected { background: #123247; color: #E9F1FF; }
QSplitter::handle { background: #263143; }
QLabel#Header { color: #00D8FF; font-weight: 700; font-size: 13pt; }
QLabel#PulsarBadge { background: #111A2E; border: 1px solid #263143; border-radius: 8px; padding: 8px; color: #E9F1FF; font-weight: 600; }
QPushButton#InformationTabButton {
    background: #111A2E;
    border: 1px solid #263143;
    border-radius: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    font-weight: 800;
    font-size: 9pt;
    color: #9BA7B8;
}
QPushButton#InformationTabButton:hover { border-color: #00D8FF; color: #00D8FF; }
QPushButton#InformationTabButton:checked { background: #123247; border-color: #00D8FF; color: #00D8FF; }
"""
