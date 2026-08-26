"""Optional numerical cross-checks against NANOGrav PINT.

PulsarLab remains a lightweight spin/glitch analysis engine. When PINT and a
TIM file are available, this module compares predicted phase, frequency, and a
nearest-pulse residual proxy without making PINT a runtime requirement for the
headless core.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import numpy as np

from pulsarlab.core.phase_model import compute_phase
from pulsarlab.core.spin_model import compute_spin
from pulsarlab.core.types import ParModel
from pulsarlab.parsers.par_parser import parse_par, serialize_par
from pulsarlab.parsers.tim_parser import parse_tim


@dataclass(frozen=True)
class PintCheckResult:
    available: bool
    ok: bool
    message: str
    model_summary: str = ""


@dataclass(frozen=True)
class PintNumericalResult:
    available: bool
    ok: bool
    message: str
    n_toas: int = 0
    phase_max_abs_cycles: float | None = None
    frequency_max_abs_hz: float | None = None
    pint_residual_rms_seconds: float | None = None
    pulsarlab_proxy_rms_seconds: float | None = None
    model_summary: str = ""


def _import_pint():
    try:
        from pint.models import get_model  # type: ignore
        from pint.toa import get_TOAs  # type: ignore
        from pint.residuals import Residuals  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        return None, None, None, exc
    return get_model, get_TOAs, Residuals, None


def pint_available() -> bool:
    get_model, _get_toas, _residuals, _exc = _import_pint()
    return get_model is not None


def check_par_with_pint(model_or_path: ParModel | str | Path) -> PintCheckResult:
    get_model, _get_toas, _residuals, exc = _import_pint()
    if get_model is None:
        return PintCheckResult(False, False, f"pint-pulsar is not installed: {exc}")
    try:
        if isinstance(model_or_path, ParModel):
            pint_model = get_model(StringIO(serialize_par(model_or_path)))
        else:
            pint_model = get_model(str(model_or_path))
    except Exception as load_exc:  # pragma: no cover
        return PintCheckResult(True, False, f"PINT could not load this .par: {load_exc}")
    return PintCheckResult(True, True, "PINT loaded the .par model successfully.", str(pint_model)[:1200])


def _phase_values(phase) -> np.ndarray:
    """Convert a PINT Phase-like result into floating pulse turns."""
    if hasattr(phase, "int") and hasattr(phase, "frac"):
        integer = getattr(phase.int, "value", phase.int)
        fraction = getattr(phase.frac, "value", phase.frac)
        return np.asarray(integer, dtype=float) + np.asarray(fraction, dtype=float)
    value = getattr(phase, "value", phase)
    return np.asarray(value, dtype=float)


def _quantity_values(quantity, unit: str | None = None) -> np.ndarray:
    if unit is not None and hasattr(quantity, "to_value"):
        return np.asarray(quantity.to_value(unit), dtype=float)
    return np.asarray(getattr(quantity, "value", quantity), dtype=float)


def compare_with_pint(par_path: str | Path, tim_path: str | Path) -> PintNumericalResult:
    """Numerically compare PulsarLab and PINT at TOA epochs.

    A constant phase offset is removed before the phase difference is measured,
    because the two tools can choose different absolute phase origins. PINT's
    full barycentric residuals and PulsarLab's nearest-pulse proxy are reported
    separately rather than claimed to be physically identical.
    """
    get_model, get_toas, Residuals, exc = _import_pint()
    if get_model is None or get_toas is None or Residuals is None:
        return PintNumericalResult(False, False, f"pint-pulsar is not installed: {exc}")

    model, par_report = parse_par(Path(par_path), Path(par_path).name)
    toas, tim_report = parse_tim(Path(tim_path), Path(tim_path).name)
    if model is None:
        return PintNumericalResult(True, False, "PulsarLab could not parse the PAR: " + "; ".join(par_report.errors))
    if toas is None:
        return PintNumericalResult(True, False, "PulsarLab could not parse the TIM: " + "; ".join(tim_report.errors))

    try:  # pragma: no cover - depends on optional PINT data/clock environment
        pint_model = get_model(StringIO(serialize_par(model)))
        pint_toas = get_toas(str(tim_path), model=pint_model, usepickle=False)
        pint_phase = _phase_values(pint_model.phase(pint_toas, abs_phase=False))
        pint_frequency = _quantity_values(pint_model.d_phase_d_toa(pint_toas), "Hz")
        pint_residuals = Residuals(pint_toas, pint_model, subtract_mean=True)
        pint_time_residual = _quantity_values(pint_residuals.time_resids, "s")
        pint_mjd = np.asarray(pint_toas.table["mjd_float"], dtype=float)
    except Exception as compare_exc:
        return PintNumericalResult(
            True,
            False,
            f"PINT loaded but numerical comparison could not be completed: {compare_exc}",
            model_summary=str(locals().get("pint_model", ""))[:1200],
        )

    pl_phase = compute_phase(model, pint_mjd, include_glitches=True)
    pl_frequency, _, _ = compute_spin(model, pint_mjd, include_glitches=True)

    # Compare phase evolution, not arbitrary absolute phase origin.
    pint_phase_rel = pint_phase - pint_phase[0]
    pl_phase_rel = pl_phase - pl_phase[0]
    phase_delta = pl_phase_rel - pint_phase_rel
    phase_delta -= np.nanmedian(phase_delta)

    pl_fraction = pl_phase - np.rint(pl_phase)
    with np.errstate(divide="ignore", invalid="ignore"):
        pl_proxy_seconds = pl_fraction / pl_frequency

    return PintNumericalResult(
        available=True,
        ok=True,
        message="PINT numerical comparison completed.",
        n_toas=int(len(pint_mjd)),
        phase_max_abs_cycles=float(np.nanmax(np.abs(phase_delta))),
        frequency_max_abs_hz=float(np.nanmax(np.abs(pl_frequency - pint_frequency))),
        pint_residual_rms_seconds=float(np.sqrt(np.nanmean(pint_time_residual**2))),
        pulsarlab_proxy_rms_seconds=float(np.sqrt(np.nanmean(pl_proxy_seconds**2))),
        model_summary=str(pint_model)[:1200],
    )
