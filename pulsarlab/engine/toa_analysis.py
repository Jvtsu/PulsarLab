"""Vectorized relationships between model glitches and loaded TOAs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pulsarlab.core.glitch_model import group_components_by_epoch
from pulsarlab.core.types import ParModel, TOATable


@dataclass(frozen=True)
class GlitchTOASummary:
    label: str
    glep: float
    component_indices: tuple[int, ...]
    window_days: float
    toa_count: int
    before_count: int
    after_count: int
    nearest_delta_days: float | None
    median_uncertainty_us: float | None
    min_uncertainty_us: float | None
    max_uncertainty_us: float | None


def summarize_glitch_toas(
    model: ParModel,
    toas: TOATable | None,
    window_days: float = 30.0,
) -> tuple[GlitchTOASummary, ...]:
    """Summarize TOAs around each physical glitch event.

    Components sharing one GLEP are reported as one event, matching the visual
    grouping already used by the spin model.
    """
    summaries: list[GlitchTOASummary] = []
    for group in group_components_by_epoch(model.glitches):
        glep = group.get("glep")
        if glep is None:
            continue
        epoch = float(glep)
        indices = () if toas is None else tuple(int(i) for i in toas.near_mjd(epoch, window_days))
        if not indices:
            summaries.append(GlitchTOASummary(
                label=str(group.get("label", "G")),
                glep=epoch,
                component_indices=tuple(int(c.index) for c in group.get("components", [])),
                window_days=float(abs(window_days)),
                toa_count=0,
                before_count=0,
                after_count=0,
                nearest_delta_days=None,
                median_uncertainty_us=None,
                min_uncertainty_us=None,
                max_uncertainty_us=None,
            ))
            continue

        assert toas is not None
        idx = np.asarray(indices, dtype=int)
        selected_mjd = np.asarray(toas.mjd, dtype=float)[idx]
        delta = selected_mjd - epoch
        sigma = np.asarray(toas.uncertainty_us, dtype=float)[idx]
        good_sigma = sigma[np.isfinite(sigma) & (sigma > 0)]
        summaries.append(GlitchTOASummary(
            label=str(group.get("label", "G")),
            glep=epoch,
            component_indices=tuple(int(c.index) for c in group.get("components", [])),
            window_days=float(abs(window_days)),
            toa_count=int(idx.size),
            before_count=int(np.sum(delta < 0)),
            after_count=int(np.sum(delta >= 0)),
            nearest_delta_days=float(delta[int(np.argmin(np.abs(delta)))]),
            median_uncertainty_us=None if good_sigma.size == 0 else float(np.median(good_sigma)),
            min_uncertainty_us=None if good_sigma.size == 0 else float(np.min(good_sigma)),
            max_uncertainty_us=None if good_sigma.size == 0 else float(np.max(good_sigma)),
        ))
    return tuple(summaries)
