"""Glitch physics for PulsarLab.

The model follows the usual TEMPO-style expansion after a glitch epoch ``tg``:

Frequency contribution for dt = t - tg >= 0:
    Δν = GLF0 + GLF1*dt + 1/2*GLF2*dt² + GLF0D*exp(-dt/τ)

Phase contribution:
    Δφ = GLPH + GLF0*dt + 1/2*GLF1*dt² + 1/6*GLF2*dt³
          + GLF0D*τ*(1 - exp(-dt/τ))

where τ = GLTD converted from days to seconds. Inputs/outputs are cycles, Hz,
Hz/s, Hz/s² using seconds as the independent time variable.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from pulsarlab.core.types import GlitchComponent
from pulsarlab.core.units import SECONDS_PER_DAY


def _component_active(component: GlitchComponent, active_components: set[int] | None) -> bool:
    if not component.enabled:
        return False
    if active_components is None:
        return True
    return int(component.index) in active_components


def _mask_dt(component: GlitchComponent, t_seconds: np.ndarray, pepoch: float) -> tuple[np.ndarray, np.ndarray]:
    mask = np.zeros_like(t_seconds, dtype=bool)
    glep = component.glep
    if glep is None or not np.isfinite(float(glep)):
        return mask, np.array([], dtype=float)
    tg = (float(glep) - float(pepoch)) * SECONDS_PER_DAY
    mask = t_seconds >= tg
    return mask, t_seconds[mask] - tg


def _tau_seconds(component: GlitchComponent) -> float | None:
    if component.gltd is None or component.gltd <= 0:
        return None
    return float(component.gltd) * SECONDS_PER_DAY


def delta_frequency(component: GlitchComponent, t_seconds: np.ndarray, pepoch: float) -> np.ndarray:
    out = np.zeros_like(t_seconds, dtype=float)
    mask, dt = _mask_dt(component, t_seconds, pepoch)
    if not np.any(mask):
        return out
    out[mask] += component.glf0 + component.glf1 * dt + 0.5 * component.glf2 * dt**2
    tau = _tau_seconds(component)
    if tau is not None and component.glf0d != 0.0:
        out[mask] += component.glf0d * np.exp(-dt / tau)
    return out


def delta_frequency_derivative(component: GlitchComponent, t_seconds: np.ndarray, pepoch: float) -> np.ndarray:
    out = np.zeros_like(t_seconds, dtype=float)
    mask, dt = _mask_dt(component, t_seconds, pepoch)
    if not np.any(mask):
        return out
    out[mask] += component.glf1 + component.glf2 * dt
    tau = _tau_seconds(component)
    if tau is not None and component.glf0d != 0.0:
        out[mask] += -(component.glf0d / tau) * np.exp(-dt / tau)
    return out


def delta_frequency_second_derivative(component: GlitchComponent, t_seconds: np.ndarray, pepoch: float) -> np.ndarray:
    out = np.zeros_like(t_seconds, dtype=float)
    mask, dt = _mask_dt(component, t_seconds, pepoch)
    if not np.any(mask):
        return out
    out[mask] += component.glf2
    tau = _tau_seconds(component)
    if tau is not None and component.glf0d != 0.0:
        out[mask] += (component.glf0d / tau**2) * np.exp(-dt / tau)
    return out


def delta_phase(component: GlitchComponent, t_seconds: np.ndarray, pepoch: float) -> np.ndarray:
    out = np.zeros_like(t_seconds, dtype=float)
    mask, dt = _mask_dt(component, t_seconds, pepoch)
    if not np.any(mask):
        return out
    out[mask] += component.glph + component.glf0 * dt + 0.5 * component.glf1 * dt**2 + (1.0 / 6.0) * component.glf2 * dt**3
    tau = _tau_seconds(component)
    if tau is not None and component.glf0d != 0.0:
        out[mask] += component.glf0d * tau * (1.0 - np.exp(-dt / tau))
    return out


def sum_glitches(
    components: tuple[GlitchComponent, ...] | list[GlitchComponent],
    t_seconds: np.ndarray,
    pepoch: float,
    quantity: str,
    active_components: set[int] | None = None,
) -> np.ndarray:
    funcs = {
        "phase": delta_phase,
        "f0": delta_frequency,
        "f1": delta_frequency_derivative,
        "f2": delta_frequency_second_derivative,
    }
    if quantity not in funcs:
        raise ValueError(f"Unknown glitch quantity {quantity!r}")
    total = np.zeros_like(t_seconds, dtype=float)
    fn = funcs[quantity]
    for component in components:
        if _component_active(component, active_components):
            total += fn(component, t_seconds, pepoch)
    return total


def group_components_by_epoch(components: tuple[GlitchComponent, ...] | list[GlitchComponent], tolerance_days: float = 1e-9) -> list[dict]:
    """Group components with the same GLEP for visual/scientific summaries."""
    buckets: dict[float, list[GlitchComponent]] = defaultdict(list)
    no_epoch: list[GlitchComponent] = []
    for comp in components:
        if comp.glep is None:
            no_epoch.append(comp)
            continue
        key = round(float(comp.glep) / tolerance_days) * tolerance_days
        buckets[key].append(comp)
    groups: list[dict] = []
    for key in sorted(buckets):
        comps = tuple(sorted(buckets[key], key=lambda c: c.index))
        groups.append({
            "glep": float(np.mean([c.glep for c in comps if c.glep is not None])),
            "components": comps,
            "label": "G" + "/".join(str(c.index) for c in comps),
            "has_transient": any(c.has_transient for c in comps),
            "enabled": any(c.enabled for c in comps),
        })
    for comp in no_epoch:
        groups.append({"glep": None, "components": (comp,), "label": f"G{comp.index}?", "has_transient": comp.has_transient, "enabled": comp.enabled})
    return groups
