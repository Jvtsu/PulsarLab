"""Graphical Windows launcher for frozen PulsarLab builds.

It accepts optional PAR, DAT, and TIM paths from file associations or drag/drop,
logs unexpected startup failures, and shows a user-facing dialog instead of
silently closing when the executable is built without a console.
"""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sys
import traceback


def classify_paths(values: list[str]) -> tuple[str | None, str | None, str | None]:
    """Classify at most one .par, .dat, and .tim path without argparse."""
    found: dict[str, str] = {}
    for value in values:
        suffix = Path(value).suffix.lower().lstrip(".")
        if suffix not in {"par", "dat", "tim"}:
            continue
        if suffix not in found:
            found[suffix] = value
    return found.get("par"), found.get("dat"), found.get("tim")


def _log_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PulsarLab"
    root.mkdir(parents=True, exist_ok=True)
    return root / "pulsarlab-crash.log"


def _show_error(message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv[:1])
        QMessageBox.critical(
            None,
            "PulsarLab",
            f"PulsarLab no pudo iniciarse.\n\n{message}\n\n"
            f"Se guardó un informe en:\n{_log_path()}",
        )
        app.processEvents()
    except Exception:
        pass


def _smoke_test() -> int:
    """Build-time GUI smoke test used by the Windows packaging pipeline."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from pulsarlab.ui.main_window import MainWindow
    from pulsarlab.ui.theme import APP_QSS

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    for view in ("spin_analysis", "glitches_toas", "residuals", "datasets"):
        window.workspace.set_view(view)
        app.processEvents()
    QTimer.singleShot(250, app.quit)
    result = int(app.exec())
    window.close()
    return result


def main() -> int:
    try:
        if "--smoke-test" in sys.argv[1:]:
            return _smoke_test()

        from pulsarlab.ui.main_window import run_app

        initial_par, initial_dat, initial_tim = classify_paths(sys.argv[1:])
        return int(run_app(initial_par, initial_dat, initial_tim))
    except Exception as exc:  # frozen GUI must not disappear without feedback
        report = (
            f"[{datetime.now().isoformat(timespec='seconds')}]\n"
            f"Python: {sys.version}\n"
            f"Executable: {sys.executable}\n"
            f"Arguments: {sys.argv!r}\n\n"
            f"{traceback.format_exc()}\n"
        )
        path = _log_path()
        try:
            path.write_text(report, encoding="utf-8")
        except Exception:
            pass
        _show_error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
