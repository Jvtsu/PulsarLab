"""Optional Astropy bridge for time/unit/coordinate checks.

PulsarLab keeps its numerical core NumPy-first for speed and portability.  This
module uses Astropy when available to validate astronomical quantities and to
cross-check simple MJD-to-second conversions used by the spin/glitch model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pulsarlab.core.units import SECONDS_PER_DAY

try:  # pragma: no cover - exercised in optional environments
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astropy.time import Time
except Exception:  # pragma: no cover - default lightweight environment
    u = None
    Time = None
    SkyCoord = None


@dataclass(frozen=True)
class AstropyAvailability:
    available: bool
    reason: str = ""


def availability() -> AstropyAvailability:
    if Time is None or u is None:
        return AstropyAvailability(False, "Astropy is not installed.")
    return AstropyAvailability(True)


def require_astropy() -> None:
    if not availability().available:
        raise RuntimeError("Astropy support requires installing astropy.")


def mjd_to_seconds_astropy(mjd: Any, reference_mjd: float, scale: str = "tdb") -> np.ndarray:
    """Return seconds elapsed from reference MJD using Astropy Time.

    This is primarily a validation/cross-check helper.  The production spin
    model still uses the direct NumPy expression for speed; both must agree for
    ordinary MJD differences.
    """
    require_astropy()
    t = Time(np.asarray(mjd, dtype=float), format="mjd", scale=scale)
    ref = Time(float(reference_mjd), format="mjd", scale=scale)
    return np.asarray((t - ref).to_value(u.s), dtype=float)


def validate_mjd_with_astropy(mjd: Any, scale: str = "tdb") -> tuple[bool, str]:
    """Check that an MJD or MJD array can be represented by Astropy Time."""
    if not availability().available:
        return True, "Astropy not installed; skipped strict MJD validation."
    try:
        Time(np.asarray(mjd, dtype=float), format="mjd", scale=scale)
    except Exception as exc:
        return False, f"Astropy could not parse MJD values: {exc}"
    return True, ""


def parse_skycoord_from_par(params: dict[str, Any]) -> tuple[object | None, str]:
    """Parse RAJ/DECJ or ELONG/ELAT when Astropy is available.

    Returns ``(coord, warning)``.  PulsarLab does not currently use astrometric
    terms in its spin-only model; this hook prevents malformed coordinates from
    silently passing through once users start importing richer .par files.
    """
    if not availability().available:
        return None, ""
    raj = params.get("RAJ") or params.get("RA")
    decj = params.get("DECJ") or params.get("DEC")
    if raj is None or decj is None:
        return None, ""
    try:
        coord = SkyCoord(str(raj), str(decj), unit=(u.hourangle, u.deg), frame="icrs")
    except Exception as exc:
        return None, f"Astropy could not parse RAJ/DECJ coordinates: {exc}"
    return coord, ""


def seconds_per_day_astropy() -> float:
    """Return seconds/day via Astropy when present, else the local constant."""
    if not availability().available:
        return SECONDS_PER_DAY
    return float(np.asarray((1 * u.day).to_value(u.s), dtype=float).item())
