"""Physical units and small unit helpers for PulsarLab."""

from __future__ import annotations

import numpy as np

SECONDS_PER_DAY: float = 86400.0
MICROSECONDS_PER_SECOND: float = 1_000_000.0
F1_DISPLAY_SCALE: float = 1e-15
F2_DISPLAY_SCALE: float = 1e-24
F3_DISPLAY_SCALE: float = 1e-33


def mjd_to_seconds(mjd, reference_mjd: float) -> np.ndarray:
    """Return seconds elapsed since ``reference_mjd``."""
    return (np.asarray(mjd, dtype=float) - float(reference_mjd)) * SECONDS_PER_DAY


def seconds_to_days(seconds) -> np.ndarray:
    return np.asarray(seconds, dtype=float) / SECONDS_PER_DAY


def microseconds_to_seconds(microseconds) -> np.ndarray:
    """Convert TOA uncertainties from microseconds to seconds in one place."""
    return np.asarray(microseconds, dtype=float) / MICROSECONDS_PER_SECOND


def seconds_to_microseconds(seconds) -> np.ndarray:
    return np.asarray(seconds, dtype=float) * MICROSECONDS_PER_SECOND


def mjd_difference_seconds_reference(mjd, reference_mjd: float) -> np.ndarray:
    """Reference MJD-to-seconds conversion used by tests."""
    return mjd_to_seconds(mjd, reference_mjd)
