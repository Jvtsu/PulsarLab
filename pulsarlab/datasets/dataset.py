"""Immutable project objects with independently optional PAR/DAT/TIM data."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
import hashlib
import json
import math

import numpy as np

from pulsarlab.core.types import ObservationTable, ParModel, TOATable


def _safe_json(value: Any) -> str:
    def default(obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if hasattr(obj, "fingerprint"):
            return obj.fingerprint()
        return repr(obj)
    return json.dumps(value, default=default, sort_keys=True)


def _array_digest(array: np.ndarray | None) -> str | None:
    if array is None:
        return None
    arr = np.ascontiguousarray(np.asarray(array))
    h = hashlib.blake2b(digest_size=12)
    h.update(str(arr.dtype).encode("ascii", errors="replace"))
    h.update(str(arr.shape).encode("ascii"))
    h.update(arr.tobytes())
    return h.hexdigest()


def _valid_span(span: tuple[float, float] | None) -> tuple[float, float] | None:
    if span is None:
        return None
    try:
        lo, hi = float(span[0]), float(span[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return None
    return (lo, hi) if lo <= hi else (hi, lo)


@dataclass(frozen=True)
class PulsarProject:
    """One analysis project whose PAR, DAT and TIM components are optional.

    A project can be assembled incrementally. Scientific model computation only
    requires ``par``; processed residual diagnostics additionally require
    ``observations``; glitch/TOA analysis additionally uses ``toas``.
    """

    dataset_id: str
    name: str
    par: ParModel | None = None
    observations: ObservationTable | None = None
    toas: TOATable | None = None
    visible: bool = True
    active_components: frozenset[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def project_id(self) -> str:
        return self.dataset_id

    @property
    def pulsar_name(self) -> str:
        return self.par.pulsar_name if self.par is not None else "Unidentified"

    @property
    def n_observations(self) -> int:
        return 0 if self.observations is None else self.observations.n

    @property
    def n_toas(self) -> int:
        return 0 if self.toas is None else self.toas.n

    @property
    def has_model(self) -> bool:
        return self.par is not None

    @property
    def has_observations(self) -> bool:
        return self.observations is not None

    @property
    def has_toas(self) -> bool:
        return self.toas is not None

    @property
    def file_kinds(self) -> tuple[str, ...]:
        kinds = []
        if self.par is not None:
            kinds.append("PAR")
        if self.observations is not None:
            kinds.append("DAT")
        if self.toas is not None:
            kinds.append("TIM")
        return tuple(kinds)

    @property
    def mjd_span(self) -> tuple[float, float]:
        """Union of model validity, DAT and TIM spans.

        Returns NaNs only for an impossible empty project.
        """
        spans: list[tuple[float, float]] = []
        if self.observations is not None:
            span = _valid_span(self.observations.mjd_span)
            if span is not None:
                spans.append(span)
        if self.toas is not None:
            span = _valid_span(self.toas.mjd_span)
            if span is not None:
                spans.append(span)
        if self.par is not None:
            start, finish = self.par.start, self.par.finish
            if start is not None and finish is not None:
                spans.append((min(float(start), float(finish)), max(float(start), float(finish))))
            elif start is not None:
                spans.append((float(start), float(start)))
            elif finish is not None:
                spans.append((float(finish), float(finish)))
        if not spans:
            if self.par is not None:
                epochs = [float(g.glep) for g in self.par.glitches if g.glep is not None]
                if epochs:
                    return (min(epochs), max(epochs))
                return (self.par.pepoch, self.par.pepoch)
            return (float("nan"), float("nan"))
        return (min(s[0] for s in spans), max(s[1] for s in spans))

    @property
    def model_span(self) -> tuple[float, float] | None:
        """Best interval for evaluating a loaded model."""
        if self.par is None:
            return None
        if self.par.start is not None and self.par.finish is not None:
            return (min(self.par.start, self.par.finish), max(self.par.start, self.par.finish))
        spans = []
        if self.observations is not None:
            span = _valid_span(self.observations.mjd_span)
            if span is not None:
                spans.append(span)
        if self.toas is not None:
            span = _valid_span(self.toas.mjd_span)
            if span is not None:
                spans.append(span)
        if spans:
            return (min(x[0] for x in spans), max(x[1] for x in spans))
        epochs = [float(g.glep) for g in self.par.glitches if g.glep is not None]
        if epochs:
            lo, hi = min(epochs), max(epochs)
            pad = max(30.0, 0.05 * max(1.0, hi - lo))
            return (lo - pad, hi + pad)
        return (self.par.pepoch - 365.25, self.par.pepoch + 365.25)

    def with_visibility(self, visible: bool) -> "PulsarProject":
        return replace(self, visible=bool(visible))

    def with_active_components(self, components: set[int] | None) -> "PulsarProject":
        return replace(self, active_components=None if components is None else frozenset(int(x) for x in components))

    def with_par(self, par: ParModel | None, **metadata: Any) -> "PulsarProject":
        meta = dict(self.metadata)
        meta.update(metadata)
        return replace(self, par=par, metadata=meta)

    def with_observations(self, observations: ObservationTable | None, **metadata: Any) -> "PulsarProject":
        meta = dict(self.metadata)
        meta.update(metadata)
        return replace(self, observations=observations, metadata=meta)

    def with_toas(self, toas: TOATable | None, **metadata: Any) -> "PulsarProject":
        meta = dict(self.metadata)
        meta.update(metadata)
        return replace(self, toas=toas, metadata=meta)

    def scientific_signature(self) -> str:
        obs = self.observations
        toas = self.toas
        payload = {
            "project_id": self.dataset_id,
            "par": None if self.par is None else self.par.fingerprint(),
            "observations": None if obs is None else {
                "mjd": _array_digest(obs.mjd),
                "f0": _array_digest(obs.f0),
                "f0_err": _array_digest(obs.f0_err),
                "f1": _array_digest(obs.f1),
                "f1_err": _array_digest(obs.f1_err),
                "f2": _array_digest(obs.f2),
                "f2_err": _array_digest(obs.f2_err),
            },
            "toas": None if toas is None else {
                "mjd": _array_digest(toas.mjd),
                "uncertainty_us": _array_digest(toas.uncertainty_us),
                "frequency_mhz": _array_digest(toas.frequency_mhz),
                "pulse_number": _array_digest(toas.pulse_number),
                "phase_offset": _array_digest(toas.phase_offset),
            },
            "active_components": None if self.active_components is None else sorted(self.active_components),
        }
        return hashlib.sha256(_safe_json(payload).encode("utf-8")).hexdigest()[:24]


# Backward-compatible public name used by older extensions and scripts.
Dataset = PulsarProject
