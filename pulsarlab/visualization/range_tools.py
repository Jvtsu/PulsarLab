"""UI-free utilities for controlling the MJD interval shown in plots."""

from __future__ import annotations

from math import isfinite
from typing import Iterable

MJDRange = tuple[float, float]


def _extract_span(project) -> MJDRange | None:
    span = getattr(project, "mjd_span", None)
    if span is None:
        observations = getattr(project, "observations", None)
        span = getattr(observations, "mjd_span", None)
    if span is None or len(span) != 2:
        return None
    try:
        lo, hi = float(span[0]), float(span[1])
    except (TypeError, ValueError):
        return None
    if not (isfinite(lo) and isfinite(hi)):
        return None
    if hi < lo:
        lo, hi = hi, lo
    if hi == lo:
        lo -= 0.5
        hi += 0.5
    return (lo, hi)


def compute_visible_mjd_span(datasets: Iterable) -> MJDRange | None:
    """Return the union of model, DAT, or TIM spans for visible projects."""
    spans = [span for dataset in datasets if (span := _extract_span(dataset)) is not None]
    if not spans:
        return None
    return (min(span[0] for span in spans), max(span[1] for span in spans))


def normalise_mjd_range(start: float, end: float, fallback: MJDRange | None = None) -> MJDRange | None:
    try:
        lo = float(start)
        hi = float(end)
    except (TypeError, ValueError):
        return fallback
    if not (isfinite(lo) and isfinite(hi)):
        return fallback
    if hi < lo:
        lo, hi = hi, lo
    if hi == lo:
        lo -= 0.5
        hi += 0.5
    return (lo, hi)


def apply_mjd_range_to_figure(fig, mjd_range: MJDRange | None) -> int:
    if mjd_range is None:
        return 0
    lo, hi = normalise_mjd_range(mjd_range[0], mjd_range[1], None) or mjd_range
    count = 0
    for ax in getattr(fig, "axes", []):
        try:
            ax.set_xlim(lo, hi)
            count += 1
        except Exception:
            continue
    return count
