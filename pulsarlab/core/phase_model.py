"""Analytic phase model and phase derivatives."""

from __future__ import annotations

import numpy as np

from pulsarlab.core.types import ParModel
from pulsarlab.core.units import mjd_to_seconds
from pulsarlab.core.spin_model import compute_spin
from pulsarlab.core.glitch_model import sum_glitches


def compute_phase(model: ParModel, mjd, include_glitches: bool = True, active_components: set[int] | None = None) -> np.ndarray:
    mjd = np.asarray(mjd, dtype=float)
    t = mjd_to_seconds(mjd, model.pepoch)
    phase = (
        model.f0 * t
        + 0.5 * model.f1 * t**2
        + (1.0 / 6.0) * model.f2 * t**3
        + (1.0 / 24.0) * model.f3 * t**4
    )
    if include_glitches and model.glitches:
        phase = phase + sum_glitches(model.glitches, t, model.pepoch, "phase", active_components)
    return phase


def compute_phase_bundle(model: ParModel, mjd, include_glitches: bool = True, active_components: set[int] | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    phase = compute_phase(model, mjd, include_glitches, active_components)
    f0, f1, _ = compute_spin(model, mjd, include_glitches, active_components)
    return phase, f0, f1
