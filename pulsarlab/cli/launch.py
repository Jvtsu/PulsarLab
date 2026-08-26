"""Command-line entry point for PulsarLab."""

from __future__ import annotations

import argparse
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plab",
        description="Launch PulsarLab with optional PAR/DAT/TIM files in any order.",
    )
    parser.add_argument("files", nargs="*", help="Optional .par, .dat, and/or .tim files")
    parser.add_argument("--selfcheck", action="store_true", help="Run headless physics self-check and exit")
    args = parser.parse_args(argv)

    if args.selfcheck:
        from pulsarlab.scripts_api import run_selfcheck
        run_selfcheck()
        return 0

    initial_par, initial_dat, initial_tim = _classify_files(args.files, parser)
    try:
        from pulsarlab.ui.main_window import run_app
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("PySide6 is not installed. Install with: pip install PySide6")
            return 2
        raise
    return run_app(initial_par, initial_dat, initial_tim)
