"""Small linear fitting utilities for PulsarLab.

The current fitter estimates spin-polynomial coefficients while keeping glitch
components fixed. This is intentionally conservative and UI-free.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from pulsarlab.core.types import ParModel
from pulsarlab.core.units import mjd_to_seconds


def _weighted_lstsq(A: np.ndarray, y: np.ndarray, sigma: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(y) & np.all(np.isfinite(A), axis=1)
    if sigma is not None:
        sigma = np.asarray(sigma, dtype=float)
        mask &= np.isfinite(sigma) & (sigma > 0)
    if int(mask.sum()) < A.shape[1]:
        raise ValueError("Not enough valid observations for the requested fit.")
    Am = A[mask]
    ym = y[mask]
    if sigma is not None:
        w = 1.0 / sigma[mask]
        Am = Am * w[:, None]
        ym = ym * w
    coeff, *_ = np.linalg.lstsq(Am, ym, rcond=None)
    cov = np.linalg.pinv(Am.T @ Am)
    return coeff, cov


def fit_spin_polynomial(model: ParModel, mjd, f0_obs, f0_err=None, degree: int = 2) -> tuple[ParModel, dict[str, float]]:
    if degree < 0 or degree > 3:
        raise ValueError("degree must be between 0 and 3")
    t = mjd_to_seconds(mjd, model.pepoch)
    cols = [np.ones_like(t)]
    if degree >= 1:
        cols.append(t)
    if degree >= 2:
        cols.append(0.5 * t**2)
    if degree >= 3:
        cols.append((1.0 / 6.0) * t**3)
    A = np.column_stack(cols)
    coeff, cov = _weighted_lstsq(A, np.asarray(f0_obs, dtype=float), None if f0_err is None else np.asarray(f0_err, dtype=float))
    keys = ["F0", "F1", "F2", "F3"][:degree+1]
    new_params = dict(model.params)
    uncertainties = {}
    for i, key in enumerate(keys):
        new_params[key] = float(coeff[i])
        uncertainties[key] = float(np.sqrt(max(cov[i, i], 0.0)))
    return replace(model, params=new_params), uncertainties
