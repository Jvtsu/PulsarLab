"""UI-free scientific dataclasses used throughout PulsarLab."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class GlitchComponent:
    """Single TEMPO-style glitch component.

    Indices are one-based to match parameters such as ``GLEP_1`` in .par files.
    Multiple components may share one GLEP and therefore represent a single
    physical event with several permanent or transient components.
    """

    index: int
    glep: float | None = None
    glph: float = 0.0
    glf0: float = 0.0
    glf1: float = 0.0
    glf2: float = 0.0
    glf0d: float = 0.0
    gltd: float | None = None  # days
    enabled: bool = True
    raw: dict[str, float] = field(default_factory=dict)

    @property
    def has_epoch(self) -> bool:
        return self.glep is not None and np.isfinite(float(self.glep))

    @property
    def has_transient(self) -> bool:
        return self.glf0d != 0.0 and self.gltd is not None and self.gltd > 0

    def with_enabled(self, enabled: bool) -> "GlitchComponent":
        return replace(self, enabled=bool(enabled))

    def fingerprint(self) -> tuple:
        return (
            int(self.index),
            None if self.glep is None else float(self.glep),
            float(self.glph), float(self.glf0), float(self.glf1), float(self.glf2),
            float(self.glf0d), None if self.gltd is None else float(self.gltd),
            bool(self.enabled),
        )


@dataclass(frozen=True)
class ParModel:
    """Parsed timing model from a ``.par`` file."""

    params: dict[str, Any]
    glitches: tuple[GlitchComponent, ...] = ()
    source_name: str = "model.par"

    @property
    def pepoch(self) -> float:
        return float(self.params["PEPOCH"])

    @property
    def f0(self) -> float:
        return float(self.params["F0"])

    @property
    def f1(self) -> float:
        return float(self.params.get("F1", 0.0))

    @property
    def f2(self) -> float:
        return float(self.params.get("F2", 0.0))

    @property
    def f3(self) -> float:
        return float(self.params.get("F3", 0.0))

    @property
    def start(self) -> float | None:
        return float(self.params["START"]) if "START" in self.params else None

    @property
    def finish(self) -> float | None:
        return float(self.params["FINISH"]) if "FINISH" in self.params else None

    @property
    def pulsar_name(self) -> str:
        for key in ("PSRJ", "PSRB", "PSR", "NAME", "PULSAR", "SOURCE"):
            value = self.params.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return "Unidentified"

    def fingerprint(self) -> tuple:
        scalar = tuple(
            (k, self.params.get(k))
            for k in sorted(self.params)
            if k.upper() != "GLITCHES"
        )
        return scalar + (("glitches", tuple(g.fingerprint() for g in self.glitches)),)


@dataclass(frozen=True)
class ObservationTable:
    """Parsed observational or processed spin-evolution data."""

    mjd: np.ndarray
    f0: np.ndarray
    f0_err: np.ndarray
    f1: np.ndarray | None = None
    f1_err: np.ndarray | None = None
    f2: np.ndarray | None = None
    f2_err: np.ndarray | None = None
    source_name: str = "data.dat"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.mjd)
        for name in ("f0", "f0_err", "f1", "f1_err", "f2", "f2_err"):
            arr = getattr(self, name)
            if arr is not None and len(arr) != n:
                raise ValueError(f"Column {name} has length {len(arr)} but mjd has length {n}.")

    @property
    def n(self) -> int:
        return int(len(self.mjd))

    @property
    def mjd_span(self) -> tuple[float, float]:
        if self.n == 0:
            return (float("nan"), float("nan"))
        return (float(np.nanmin(self.mjd)), float(np.nanmax(self.mjd)))

    def filtered_by_mjd(self, start: float | None, finish: float | None) -> "ObservationTable":
        if self.n == 0:
            return self
        lo = float(start) if start is not None else float(np.nanmin(self.mjd))
        hi = float(finish) if finish is not None else float(np.nanmax(self.mjd))
        if lo > hi:
            lo, hi = hi, lo
        mask = (self.mjd >= lo) & (self.mjd <= hi)
        kwargs = {}
        for name in ("f1", "f1_err", "f2", "f2_err"):
            value = getattr(self, name)
            kwargs[name] = None if value is None else np.asarray(value)[mask]
        meta = dict(self.metadata)
        meta.update({
            "observations_total": self.n,
            "observations_used": int(mask.sum()),
            "observations_outside_model_range": int((~mask).sum()),
            "filter_start": lo,
            "filter_finish": hi,
        })
        return ObservationTable(
            mjd=np.asarray(self.mjd)[mask],
            f0=np.asarray(self.f0)[mask],
            f0_err=np.asarray(self.f0_err)[mask],
            source_name=self.source_name,
            metadata=meta,
            **kwargs,
        )


@dataclass(frozen=True)
class TOA:
    """One pulse time of arrival from a TEMPO/TEMPO2 ``.tim`` file.

    ``uncertainty_us`` follows the conventional FORMAT 1 unit. Flags are kept
    as immutable key/value pairs so one TOA remains safe to cache and compare.
    """

    name: str
    frequency_mhz: float
    mjd: float
    uncertainty_us: float
    observatory: str
    pulse_number: float | None = None
    phase_offset: float | None = None
    flags: tuple[tuple[str, str], ...] = ()
    raw_line: str = ""
    line_number: int | None = None

    @property
    def flag_map(self) -> Mapping[str, str]:
        return dict(self.flags)


@dataclass(frozen=True)
class TOATable:
    """Columnar collection of TOAs optimized for range and glitch searches."""

    mjd: np.ndarray
    uncertainty_us: np.ndarray
    frequency_mhz: np.ndarray
    names: tuple[str, ...]
    observatories: tuple[str, ...]
    pulse_number: np.ndarray | None = None
    phase_offset: np.ndarray | None = None
    flags: tuple[tuple[tuple[str, str], ...], ...] = ()
    raw_lines: tuple[str, ...] = ()
    source_name: str = "toas.tim"
    format_name: str = "TEMPO2 FORMAT 1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.mjd)
        required = {
            "uncertainty_us": self.uncertainty_us,
            "frequency_mhz": self.frequency_mhz,
            "names": self.names,
            "observatories": self.observatories,
        }
        for name, values in required.items():
            if len(values) != n:
                raise ValueError(f"TOA column {name} has length {len(values)} but mjd has length {n}.")
        for name in ("pulse_number", "phase_offset"):
            values = getattr(self, name)
            if values is not None and len(values) != n:
                raise ValueError(f"TOA column {name} has length {len(values)} but mjd has length {n}.")
        if self.flags and len(self.flags) != n:
            raise ValueError(f"TOA flags have length {len(self.flags)} but mjd has length {n}.")
        if self.raw_lines and len(self.raw_lines) != n:
            raise ValueError(f"TOA raw_lines have length {len(self.raw_lines)} but mjd has length {n}.")

    @property
    def n(self) -> int:
        return int(len(self.mjd))

    @property
    def mjd_span(self) -> tuple[float, float]:
        if self.n == 0:
            return (float("nan"), float("nan"))
        return (float(np.nanmin(self.mjd)), float(np.nanmax(self.mjd)))

    @property
    def uncertainty_seconds(self) -> np.ndarray:
        from pulsarlab.core.units import microseconds_to_seconds
        return microseconds_to_seconds(self.uncertainty_us)

    def near_mjd(self, epoch: float, window_days: float) -> np.ndarray:
        """Return sorted integer indices within ``window_days`` of ``epoch``."""
        if self.n == 0:
            return np.array([], dtype=int)
        mjd = np.asarray(self.mjd, dtype=float)
        lo = float(epoch) - abs(float(window_days))
        hi = float(epoch) + abs(float(window_days))
        # Parser-produced tables are sorted, so the common path is O(log n + k).
        # Hand-built TOATable objects remain correct even when unsorted.
        if np.any(np.diff(mjd) < 0):
            return np.flatnonzero((mjd >= lo) & (mjd <= hi)).astype(int, copy=False)
        left = int(np.searchsorted(mjd, lo, side="left"))
        right = int(np.searchsorted(mjd, hi, side="right"))
        return np.arange(left, right, dtype=int)

    def row(self, index: int) -> TOA:
        i = int(index)
        pn = None if self.pulse_number is None or not np.isfinite(self.pulse_number[i]) else float(self.pulse_number[i])
        po = None if self.phase_offset is None or not np.isfinite(self.phase_offset[i]) else float(self.phase_offset[i])
        flags = self.flags[i] if self.flags else ()
        raw = self.raw_lines[i] if self.raw_lines else ""
        return TOA(
            name=self.names[i],
            frequency_mhz=float(self.frequency_mhz[i]),
            mjd=float(self.mjd[i]),
            uncertainty_us=float(self.uncertainty_us[i]),
            observatory=self.observatories[i],
            pulse_number=pn,
            phase_offset=po,
            flags=flags,
            raw_line=raw,
            line_number=i + 1,
        )
