"""Analytic spin-evolution model."""

from __future__ import annotations

import numpy as np

from pulsarlab.core.types import ParModel
from pulsarlab.core.units import mjd_to_seconds
from pulsarlab.core.glitch_model import sum_glitches


def spin_polynomial(model: ParModel, mjd) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return polynomial F0, F1, F2 without glitches."""
    mjd = np.asarray(mjd, dtype=float)
    t = mjd_to_seconds(mjd, model.pepoch)
    f0 = model.f0 + model.f1 * t + 0.5 * model.f2 * t**2 + (1.0 / 6.0) * model.f3 * t**3
    f1 = model.f1 + model.f2 * t + 0.5 * model.f3 * t**2
    f2 = model.f2 + model.f3 * t
    return f0, f1, f2


def compute_spin(
    model: ParModel,
    mjd,
    include_glitches: bool = True,
    active_components: set[int] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return F0(t), F1(t), F2(t) using seconds-based derivatives."""
    mjd = np.asarray(mjd, dtype=float)
    f0, f1, f2 = spin_polynomial(model, mjd)
    if include_glitches and model.glitches:
        t = mjd_to_seconds(mjd, model.pepoch)
        f0 = f0 + sum_glitches(model.glitches, t, model.pepoch, "f0", active_components)
        f1 = f1 + sum_glitches(model.glitches, t, model.pepoch, "f1", active_components)
        f2 = f2 + sum_glitches(model.glitches, t, model.pepoch, "f2", active_components)
    return f0, f1, f2
