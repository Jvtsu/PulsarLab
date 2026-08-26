"""Residual and diagnostic computations.

PulsarLab residuals are processed-frequency residuals, not full TOA timing
residuals. Convention: observed - model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ResidualStats:
    n: int
    rms: float
    mean: float
    weighted_rms: float | None = None
    chi2_red: float | None = None


def residual(observed, model) -> np.ndarray:
    return np.asarray(observed, dtype=float) - np.asarray(model, dtype=float)


def stats(residuals, sigma=None, dof: int | None = None) -> ResidualStats:
    r = np.asarray(residuals, dtype=float)
    finite = np.isfinite(r)
    if not np.any(finite):
        return ResidualStats(0, float("nan"), float("nan"), None, None)
    r = r[finite]
    rms = float(np.sqrt(np.mean(r**2)))
    mean = float(np.mean(r))
    wrms = None
    chi2_red = None
    if sigma is not None:
        s = np.asarray(sigma, dtype=float)[finite]
        good = np.isfinite(s) & (s > 0)
        if np.any(good):
            weights = 1.0 / s[good] ** 2
            wrms = float(np.sqrt(np.sum(weights * r[good] ** 2) / np.sum(weights)))
            denom = max(1, (int(np.sum(good)) - (dof or 0)))
            chi2_red = float(np.sum((r[good] / s[good]) ** 2) / denom)
    return ResidualStats(int(r.size), rms, mean, wrms, chi2_red)
