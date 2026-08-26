"""Parser for common TEMPO/TEMPO2 ``.tim`` pulse-arrival files.

PulsarLab intentionally parses the portable, widely used FORMAT 1 row:

``name frequency_MHz MJD uncertainty_us observatory [flags...]``

Timing directives are retained as metadata where practical and otherwise
reported instead of being silently interpreted as TOAs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pulsarlab.core.types import TOATable
from pulsarlab.parsers.par_parser import parse_float_token
from pulsarlab.parsers.reports import TimParseReport

_COMMENT_PREFIXES = ("#", "//")
_DIRECTIVES = {
    "FORMAT", "MODE", "EFAC", "EQUAD", "EMIN", "EMAX", "FMIN", "FMAX",
    "INFO", "JUMP", "SKIP", "NOSKIP", "TIME", "PHASE", "TRACK", "END",
    "INCLUDE", "DITHER", "CORRECT_TROPOSPHERE", "PLANET_SHAPIRO",
}


def _read_text(source: str | bytes | Path) -> str:
    if isinstance(source, bytes):
        return source.decode("utf-8", errors="replace")
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8", errors="replace")
    text = str(source)
    if "\n" not in text and "\r" not in text:
        path = Path(text)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return text


def _is_numeric_token(token: str) -> bool:
    try:
        parse_float_token(token)
    except ValueError:
        return False
    return True


def _parse_flags(tokens: list[str]) -> tuple[tuple[str, str], ...]:
    flags: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("-"):
            key = token.lstrip("-")
            value = "true"
            if i + 1 < len(tokens):
                candidate = tokens[i + 1]
                # A negative numeric value still belongs to the current flag;
                # only a non-numeric leading dash starts the next flag.
                if not candidate.startswith("-") or _is_numeric_token(candidate):
                    value = candidate
                    i += 1
            flags.append((key, value))
        else:
            flags.append((f"arg{i + 1}", token))
        i += 1
    return tuple(flags)


def _flag_float(flags: tuple[tuple[str, str], ...], *names: str) -> float | None:
    lookup = {key.lower(): value for key, value in flags}
    for name in names:
        if name.lower() not in lookup:
            continue
        try:
            return parse_float_token(lookup[name.lower()])
        except ValueError:
            return None
    return None


def parse_tim(source: str | bytes | Path, source_name: str | None = None) -> tuple[TOATable | None, TimParseReport]:
    """Parse common FORMAT 1 TOAs and return a sorted columnar table."""
    report = TimParseReport()
    try:
        text = _read_text(source)
    except OSError as exc:
        report.errors.append(f"Could not read TIM file '{source_name or source}': {exc.strerror or exc}.")
        return None, report
    names: list[str] = []
    frequency: list[float] = []
    mjd: list[float] = []
    uncertainty: list[float] = []
    observatories: list[str] = []
    pulse_numbers: list[float] = []
    phase_offsets: list[float] = []
    all_flags: list[tuple[tuple[str, str], ...]] = []
    raw_lines: list[str] = []
    directives: list[str] = []
    declared_format: str | None = None

    for line_number, raw in enumerate(text.splitlines(), start=1):
        report.lines_read += 1
        line = raw.strip()
        if not line or line.startswith(_COMMENT_PREFIXES):
            continue
        # Classic TEMPO uses an uppercase C in column one as a comment.
        # Do not uppercase the row: lowercase file names such as ``c`` are
        # valid FORMAT 1 TOA names.
        if raw == "C" or raw.startswith("C ") or raw.startswith("C\t"):
            continue

        parts = line.split()
        keyword = parts[0].upper()
        if keyword in _DIRECTIVES:
            report.directives_seen += 1
            directives.append(line)
            if keyword == "FORMAT" and len(parts) >= 2:
                declared_format = parts[1]
                report.format_name = f"TEMPO2 FORMAT {parts[1]}"
                if parts[1] != "1":
                    report.warnings.append(
                        f"Declared TIM FORMAT {parts[1]} is not fully supported; PulsarLab will try FORMAT 1 rows."
                    )
            elif keyword == "INCLUDE":
                report.warnings.append(
                    f"TIM INCLUDE directive on line {line_number} was not expanded; load the referenced file separately."
                )
            continue

        if len(parts) < 5:
            report.skipped_lines += 1
            report.invalid_toas += 1
            report.warnings.append(f"Skipped TIM line {line_number}: expected at least 5 columns.")
            continue

        try:
            freq = parse_float_token(parts[1])
            epoch = parse_float_token(parts[2])
            sigma_us = parse_float_token(parts[3])
        except ValueError:
            report.skipped_lines += 1
            report.invalid_toas += 1
            report.warnings.append(f"Skipped TIM line {line_number}: invalid frequency, MJD, or uncertainty.")
            continue

        if not np.isfinite(epoch) or not np.isfinite(freq) or not np.isfinite(sigma_us):
            report.skipped_lines += 1
            report.invalid_toas += 1
            report.warnings.append(f"Skipped TIM line {line_number}: non-finite numeric value.")
            continue
        if sigma_us <= 0:
            report.warnings.append(f"TIM line {line_number} has non-positive uncertainty; stored as NaN.")
            sigma_us = float("nan")

        flags = _parse_flags(parts[5:])
        pn = _flag_float(flags, "pn", "pulse", "pulsenumber")
        phase = _flag_float(flags, "phase", "padd")

        names.append(parts[0])
        frequency.append(float(freq))
        mjd.append(float(epoch))
        uncertainty.append(float(sigma_us))
        observatories.append(parts[4])
        pulse_numbers.append(float("nan") if pn is None else float(pn))
        phase_offsets.append(float("nan") if phase is None else float(phase))
        all_flags.append(flags)
        raw_lines.append(raw.rstrip("\n"))
        report.lines_used += 1

    if not mjd:
        report.errors.append("No valid TOAs were found in the .tim file.")
        return None, report

    order = np.argsort(np.asarray(mjd, dtype=float), kind="stable")
    if not np.array_equal(order, np.arange(len(mjd))):
        report.warnings.append("TOAs were not sorted by MJD; PulsarLab sorted them before analysis.")

    def _arr(values: list[float]) -> np.ndarray:
        return np.asarray(values, dtype=float)[order]

    ordered_names = tuple(names[i] for i in order)
    ordered_obs = tuple(observatories[i] for i in order)
    ordered_flags = tuple(all_flags[i] for i in order)
    ordered_raw = tuple(raw_lines[i] for i in order)
    pulse_arr = _arr(pulse_numbers)
    phase_arr = _arr(phase_offsets)
    if not np.any(np.isfinite(pulse_arr)):
        pulse_arr = None
    if not np.any(np.isfinite(phase_arr)):
        phase_arr = None

    metadata = {
        "declared_format": declared_format,
        "directives": tuple(directives),
        "lines_read": report.lines_read,
        "lines_used": report.lines_used,
        "invalid_toas": report.invalid_toas,
    }
    table = TOATable(
        mjd=_arr(mjd),
        uncertainty_us=_arr(uncertainty),
        frequency_mhz=_arr(frequency),
        names=ordered_names,
        observatories=ordered_obs,
        pulse_number=pulse_arr,
        phase_offset=phase_arr,
        flags=ordered_flags,
        raw_lines=ordered_raw,
        source_name=source_name or "toas.tim",
        format_name=report.format_name,
        metadata=metadata,
    )
    return table, report
