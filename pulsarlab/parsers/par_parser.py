"""Robust TEMPO/TEMPO2-style .par parser for PulsarLab."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from pulsarlab.core.types import GlitchComponent, ParModel
from pulsarlab.parsers.reports import ParParseReport

_FLOAT_TOKEN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?$")
_GLITCH_KEY = re.compile(r"^(GLEP|GLPH|GLF0|GLF1|GLF2|GLF0D|GLTD)_(\d+)$", re.IGNORECASE)


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


def parse_float_token(token: str) -> float:
    """Parse a TEMPO numeric token, including Fortran D exponents.

    Accepts compact uncertainty notation such as ``1.23(4)`` by taking the
    central value. Non-finite values raise ``ValueError`` because they cannot be
    safely used in physical calculations.
    """
    text = str(token).strip()
    if not text:
        raise ValueError("empty numeric token")
    if "(" in text and text.endswith(")"):
        text = text.split("(", 1)[0]
    text = text.replace("D", "E").replace("d", "e")
    if not _FLOAT_TOKEN.match(text):
        raise ValueError(f"not a numeric token: {token!r}")
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric token: {token!r}")
    return value


def _strip_comment(line: str) -> str:
    # Keep coordinates such as 05:37:47.4 intact. Comments are recognized only
    # after whitespace markers.
    for marker in (" #", " //"):
        if marker in line:
            line = line.split(marker, 1)[0]
    return line.strip()


def _parse_generic_value(token: str) -> Any:
    if ":" in token:
        return token
    try:
        return parse_float_token(token)
    except ValueError:
        return token


def _build_glitch(index: int, raw: dict[str, float], report: ParParseReport) -> GlitchComponent:
    if "GLEP" not in raw:
        report.incomplete_glitches += 1
        report.warnings.append(f"Glitch component {index} has no GLEP and will be ignored by the model.")
    gltd = raw.get("GLTD")
    if gltd is not None and gltd <= 0:
        report.warnings.append(f"Glitch component {index} has non-positive GLTD={gltd}; transient term disabled.")
        gltd = None
    return GlitchComponent(
        index=index,
        glep=raw.get("GLEP"),
        glph=raw.get("GLPH", 0.0),
        glf0=raw.get("GLF0", 0.0),
        glf1=raw.get("GLF1", 0.0),
        glf2=raw.get("GLF2", 0.0),
        glf0d=raw.get("GLF0D", 0.0),
        gltd=gltd,
        raw=dict(raw),
    )


def parse_par(source: str | bytes | Path, source_name: str | None = None) -> tuple[ParModel | None, ParParseReport]:
    """Parse a .par file into a ``ParModel`` and report."""
    report = ParParseReport()
    params: dict[str, Any] = {}
    glitches_raw: dict[int, dict[str, float]] = {}

    try:
        text = _read_text(source)
    except OSError as exc:
        report.errors.append(f"Could not read PAR file '{source_name or source}': {exc.strerror or exc}.")
        return None, report
    for raw_line in text.splitlines():
        report.lines_read += 1
        line = _strip_comment(raw_line.strip())
        if not line:
            continue
        upper = line.upper()
        if upper == "C" or upper.startswith("C ") or upper.startswith("#") or upper.startswith("//"):
            continue

        parts = line.split()
        if len(parts) < 2:
            report.skipped_lines += 1
            continue

        key = parts[0].upper()
        value = parts[1]
        report.lines_used += 1

        match = _GLITCH_KEY.match(key)
        if match:
            gkey, idx_text = match.group(1).upper(), match.group(2)
            idx = int(idx_text)
            try:
                glitches_raw.setdefault(idx, {})[gkey] = parse_float_token(value)
            except ValueError:
                report.invalid_parameters += 1
                report.warnings.append(f"Could not parse {key}={value!r} as a numeric glitch parameter.")
            continue

        params[key] = _parse_generic_value(value)

    glitches = tuple(_build_glitch(idx, glitches_raw[idx], report) for idx in sorted(glitches_raw))
    report.glitches_found = len(glitches)

    if "F0" not in params:
        report.errors.append("Required spin parameter F0 is missing.")
    if "PEPOCH" not in params:
        report.errors.append("Required reference epoch PEPOCH is missing.")

    for key in ("F0", "F1", "F2", "F3", "PEPOCH", "START", "FINISH"):
        if key in params and not isinstance(params[key], (int, float)):
            report.errors.append(f"Parameter {key} must be numeric; got {params[key]!r}.")

    if "START" in params and "FINISH" in params:
        try:
            if float(params["START"]) == float(params["FINISH"]):
                report.warnings.append("START and FINISH are identical; model grid will contain a single epoch.")
        except Exception:
            pass

    if report.errors:
        return None, report
    return ParModel(params=params, glitches=glitches, source_name=source_name or "model.par"), report


def serialize_par(model: ParModel) -> str:
    keys = ["PSRJ", "PSRB", "PSR", "RAJ", "DECJ", "F0", "F1", "F2", "F3", "PEPOCH", "START", "FINISH", "DM"]
    lines = ["# Generated by PulsarLab", ""]
    written = set()
    for key in keys:
        if key in model.params:
            value = model.params[key]
            if isinstance(value, float):
                lines.append(f"{key:<18} {value:.17g}")
            else:
                lines.append(f"{key:<18} {value}")
            written.add(key)
    for key in sorted(k for k in model.params if k not in written):
        value = model.params[key]
        if isinstance(value, float):
            lines.append(f"{key:<18} {value:.17g}")
        else:
            lines.append(f"{key:<18} {value}")
    if model.glitches:
        lines.append("")
    for g in model.glitches:
        values = {
            "GLEP": g.glep,
            "GLPH": g.glph,
            "GLF0": g.glf0,
            "GLF1": g.glf1,
            "GLF2": g.glf2,
            "GLF0D": g.glf0d,
            "GLTD": g.gltd,
        }
        for key, val in values.items():
            if val is None:
                continue
            if key == "GLEP" or float(val) != 0.0:
                lines.append(f"{key}_{g.index:<14} {float(val):.17g}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
