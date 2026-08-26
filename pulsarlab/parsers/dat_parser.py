"""Robust parser for processed pulsar spin-evolution .dat files.

The .dat format is not a universal pulsar-timing standard. PulsarLab therefore
accepts common processed-table layouts and reports any unit inference it makes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from pulsarlab.core.types import ObservationTable
from pulsarlab.core.units import F1_DISPLAY_SCALE, F2_DISPLAY_SCALE
from pulsarlab.parsers.par_parser import parse_float_token
from pulsarlab.parsers.reports import DatParseReport

_COLUMN_ALIASES = {
    "mjd": "mjd", "epoch": "mjd", "time": "mjd",
    "f0": "f0", "nu": "f0", "freq": "f0", "frequency": "f0",
    "f0_err": "f0_err", "err_f0": "f0_err", "ef0": "f0_err", "f0err": "f0_err", "sigma_f0": "f0_err",
    "f1": "f1", "nudot": "f1", "fdot": "f1",
    "f1_err": "f1_err", "err_f1": "f1_err", "ef1": "f1_err", "f1err": "f1_err", "sigma_f1": "f1_err",
    "f2": "f2", "nuddot": "f2", "fddot": "f2",
    "f2_err": "f2_err", "err_f2": "f2_err", "ef2": "f2_err", "f2err": "f2_err", "sigma_f2": "f2_err",
}

_POSITIONAL = ["mjd", "f0", "f0_err", "f1", "f1_err", "f2", "f2_err"]


def _read_text(source: str | bytes | Path) -> str:
    if isinstance(source, bytes):
        return source.decode("utf-8", errors="replace")
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8", errors="replace")
    text = str(source)
    if "\n" not in text and "\r" not in text:
        p = Path(text)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    return text


def _normalize_header_token(token: str) -> str:
    token = token.strip().lower().replace("-", "_").replace(".", "_").replace("/", "_")
    token = token.replace("σ", "sigma_")
    return _COLUMN_ALIASES.get(token, token)


def _parse_numeric_row(parts: Sequence[str]) -> list[float] | None:
    numeric = []
    for part in parts:
        try:
            numeric.append(parse_float_token(part))
        except ValueError:
            # Treat trailing text as comment/flag only after at least 3 values.
            if len(numeric) >= 3:
                break
            return None
    return numeric if len(numeric) >= 3 else None


def _maybe_scale(values: np.ndarray | None, errors: np.ndarray | None, scale: float, threshold: float) -> tuple[np.ndarray | None, np.ndarray | None, bool]:
    if values is None:
        return values, errors, False
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return values, errors, False
    if float(np.nanmedian(np.abs(finite))) > threshold:
        values = values * scale
        if errors is not None:
            errors = errors * scale
        return values, errors, True
    return values, errors, False


def _column_dict_from_rows(rows: list[list[float]], header: list[str] | None) -> dict[str, np.ndarray]:
    max_cols = max(len(r) for r in rows)
    matrix = np.full((len(rows), max_cols), np.nan, dtype=float)
    for i, row in enumerate(rows):
        matrix[i, :len(row)] = row

    columns: dict[str, np.ndarray] = {}
    if header:
        normalized = [_normalize_header_token(h) for h in header]
        for idx, key in enumerate(normalized[:max_cols]):
            if key in set(_POSITIONAL) and key not in columns:
                columns[key] = matrix[:, idx]
    if not {"mjd", "f0", "f0_err"}.issubset(columns):
        columns = {name: matrix[:, idx] for idx, name in enumerate(_POSITIONAL[:max_cols])}
    return columns


def parse_dat(source: str | bytes | Path, source_name: str | None = None) -> tuple[ObservationTable | None, DatParseReport]:
    report = DatParseReport()
    try:
        text = _read_text(source)
    except OSError as exc:
        report.errors.append(f"Could not read DAT file '{source_name or source}': {exc.strerror or exc}.")
        return None, report
    rows: list[list[float]] = []
    header: list[str] | None = None

    for raw in text.splitlines():
        report.lines_read += 1
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("#", "//")) or line.upper().startswith("C "):
            # Could still be a commented header: # MJD F0 F0_ERR
            maybe = line.lstrip("#/ ").strip()
            maybe_parts = maybe.replace(",", " ").split()
            normalized = [_normalize_header_token(p) for p in maybe_parts]
            if "mjd" in normalized and "f0" in normalized:
                header = maybe_parts
            continue
        parts = line.replace(",", " ").split()
        numeric = _parse_numeric_row(parts)
        if numeric is None:
            normalized = [_normalize_header_token(p) for p in parts]
            if "mjd" in normalized and "f0" in normalized:
                header = parts
            else:
                report.skipped_lines += 1
            continue
        rows.append(numeric)
        report.lines_used += 1

    if not rows:
        report.errors.append("No valid numeric observations were found in the .dat file.")
        return None, report

    cols = _column_dict_from_rows(rows, header)
    missing = [c for c in ("mjd", "f0", "f0_err") if c not in cols]
    if missing:
        report.errors.append("Missing required .dat columns: " + ", ".join(missing))
        return None, report

    mjd = np.asarray(cols["mjd"], dtype=float)
    f0 = np.asarray(cols["f0"], dtype=float)
    f0_err = np.asarray(cols["f0_err"], dtype=float)
    f1 = np.asarray(cols["f1"], dtype=float) if "f1" in cols else None
    f1_err = np.asarray(cols["f1_err"], dtype=float) if "f1_err" in cols else None
    f2 = np.asarray(cols["f2"], dtype=float) if "f2" in cols else None
    f2_err = np.asarray(cols["f2_err"], dtype=float) if "f2_err" in cols else None

    # Drop rows without the minimum physical information.
    mask = np.isfinite(mjd) & np.isfinite(f0) & np.isfinite(f0_err)
    dropped = int((~mask).sum())
    if dropped:
        report.warnings.append(f"Dropped {dropped} row(s) with non-finite MJD/F0/F0 uncertainty.")
    if not np.any(mask):
        report.errors.append("All rows were invalid after finite-value filtering.")
        return None, report

    mjd, f0, f0_err = mjd[mask], f0[mask], f0_err[mask]
    if f1 is not None:
        f1 = f1[mask]
    if f1_err is not None:
        f1_err = f1_err[mask]
    if f2 is not None:
        f2 = f2[mask]
    if f2_err is not None:
        f2_err = f2_err[mask]

    if np.any(f0_err <= 0):
        report.warnings.append("Some F0 uncertainties are non-positive; weighted statistics may ignore them.")
        f0_err = np.where(f0_err > 0, f0_err, np.nan)
    if f1_err is not None and np.any(f1_err <= 0):
        report.warnings.append("Some F1 uncertainties are non-positive; weighted statistics may ignore them.")
        f1_err = np.where(f1_err > 0, f1_err, np.nan)
    if f2_err is not None and np.any(f2_err <= 0):
        report.warnings.append("Some F2 uncertainties are non-positive; weighted statistics may ignore them.")
        f2_err = np.where(f2_err > 0, f2_err, np.nan)

    f1, f1_err, scaled_f1 = _maybe_scale(f1, f1_err, F1_DISPLAY_SCALE, threshold=1e-7)
    f2, f2_err, scaled_f2 = _maybe_scale(f2, f2_err, F2_DISPLAY_SCALE, threshold=1e-15)
    report.scaled_f1 = scaled_f1
    report.scaled_f2 = scaled_f2
    if scaled_f1:
        report.warnings.append("F1 appears to be in display units; converted by 1e-15 to Hz/s.")
    if scaled_f2:
        report.warnings.append("F2 appears to be in display units; converted by 1e-24 to Hz/s².")

    order = np.argsort(mjd)
    table = ObservationTable(
        mjd=mjd[order], f0=f0[order], f0_err=f0_err[order],
        f1=None if f1 is None else f1[order],
        f1_err=None if f1_err is None else f1_err[order],
        f2=None if f2 is None else f2[order],
        f2_err=None if f2_err is None else f2_err[order],
        source_name=source_name or "data.dat",
        metadata={"header_detected": header is not None, "rows_loaded": int(np.sum(mask))},
    )
    return table, report
