"""Command-line entry point for PulsarLab."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def _classify_files(files: list[str], parser: argparse.ArgumentParser) -> tuple[str | None, str | None, str | None]:
    found: dict[str, str] = {}
    for value in files:
        suffix = Path(value).suffix.lower().lstrip(".")
        if suffix not in {"par", "dat", "tim"}:
            parser.error(f"Cannot classify {value!r}; expected a .par, .dat, or .tim file.")
        if suffix in found:
            parser.error(f"Only one .{suffix} file can be loaded into the initial project.")
        found[suffix] = value
    return found.get("par"), found.get("dat"), found.get("tim")


def _run_gui_smoke_test() -> int:
    """Start the real desktop shell, visit core views, and exit cleanly.

    This is intended for CI and frozen builds. It does not load user data.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from pulsarlab.ui.main_window import MainWindow
    from pulsarlab.ui.theme import APP_QSS

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    for view in ("spin_analysis", "glitches_toas", "residuals", "datasets", "information"):
        window.workspace.set_view(view)
        app.processEvents()
    QTimer.singleShot(200, app.quit)
    try:
        return int(app.exec())
    finally:
        window.close()
        app.processEvents()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plab",
        description="Launch PulsarLab with optional PAR/DAT/TIM files in any order.",
    )
    parser.add_argument("files", nargs="*", help="Optional .par, .dat, and/or .tim files")
    parser.add_argument("--selfcheck", action="store_true", help="Run headless physics self-check and exit")
    parser.add_argument("--smoke-test", action="store_true", help="Start the GUI, visit core views, and exit (CI)")
    args = parser.parse_args(argv)

    if args.selfcheck:
        from pulsarlab.scripts_api import run_selfcheck
        run_selfcheck()
        return 0
    if args.smoke_test:
        return _run_gui_smoke_test()

    initial_par, initial_dat, initial_tim = _classify_files(args.files, parser)
    try:
        from pulsarlab.ui.main_window import run_app
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("PySide6 is not installed. Install with: pip install PySide6")
            return 2
        raise
    return run_app(initial_par, initial_dat, initial_tim)


if __name__ == "__main__":
    # This guard is required for PyInstaller. All three platform specs
    # (windows/linux/macos) point PyInstaller's Analysis directly at this
    # file, which means PyInstaller's bootloader executes it as __main__.
    # Without this guard, main() is defined but never invoked, so the
    # frozen executable would open and immediately exit doing nothing.
    raise SystemExit(main())
