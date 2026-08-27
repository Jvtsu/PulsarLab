"""Computation pipeline and cache for PulsarLab."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time

import numpy as np

from pulsarlab.core.glitch_model import group_components_by_epoch
from pulsarlab.core.phase_model import compute_phase, compute_phase_bundle
from pulsarlab.core.spin_model import compute_spin
from pulsarlab.datasets.dataset import PulsarProject
from pulsarlab.engine.residuals import residual, stats, ResidualStats
from pulsarlab.engine.toa_analysis import GlitchTOASummary, summarize_glitch_toas


class ProjectNotComputableError(ValueError):
    """Raised when scientific model computation is requested without a PAR."""


@dataclass(frozen=True)
class ModelResult:
    dataset_id: str
    model_mjd: np.ndarray
    f0_model: np.ndarray
    f1_model: np.ndarray
    f2_model: np.ndarray
    f0_noglit: np.ndarray
    f1_noglit: np.ndarray
    f2_noglit: np.ndarray
    phase: np.ndarray
    phase_dot: np.ndarray
    phase_ddot: np.ndarray
    phase_noglit: np.ndarray
    phase_dot_noglit: np.ndarray
    phase_ddot_noglit: np.ndarray
    glitch_f0: np.ndarray
    glitch_f1: np.ndarray
    glitch_f2: np.ndarray
    glitch_phase: np.ndarray
    f0_at_data: np.ndarray
    f1_at_data: np.ndarray
    f2_at_data: np.ndarray
    residual_f0: np.ndarray
    residual_f1: np.ndarray | None
    residual_f2: np.ndarray | None
    stats_f0: ResidualStats
    stats_f1: ResidualStats | None
    stats_f2: ResidualStats | None
    toa_phase: np.ndarray
    toa_frequency: np.ndarray
    glitch_groups: list[dict]
    glitch_toa_summaries: tuple[GlitchTOASummary, ...]
    computed_seconds: float


class ModelCache:
    def __init__(self) -> None:
        self._cache: dict[str, ModelResult] = {}

    def clear(self) -> None:
        self._cache.clear()

    def key(
        self,
        project: PulsarProject,
        include_glitches: bool,
        grid_points: int,
        toa_window_days: float,
        compute_toa_series: bool = True,
        summarize_toas: bool = True,
    ) -> str:
        payload = {
            "signature": project.scientific_signature(),
            "include_glitches": bool(include_glitches),
            "grid_points": int(grid_points),
            "toa_window_days": float(toa_window_days),
            "compute_toa_series": bool(compute_toa_series),
            "summarize_toas": bool(summarize_toas),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def get(self, key: str) -> ModelResult | None:
        return self._cache.get(key)

    def set(self, key: str, value: ModelResult) -> None:
        self._cache[key] = value


class Pipeline:
    """Pure scientific engine. No Qt imports and no UI state."""

    def __init__(self, cache: ModelCache | None = None) -> None:
        self.cache = cache or ModelCache()

    def model_grid(self, project: PulsarProject, n: int = 1200) -> np.ndarray:
        """Return a model grid with explicit samples around glitch epochs."""
        if project.par is None:
            raise ProjectNotComputableError("A PAR timing model is required for model computation.")
        span = project.model_span
        if span is None:
            raise ProjectNotComputableError("No valid MJD interval is available for the loaded PAR model.")
        start, finish = float(span[0]), float(span[1])
        if start == finish:
            start -= 0.5
            finish += 0.5
        base = np.linspace(start, finish, int(max(2, n)), dtype=float)
        extra: list[float] = []
        eps = 1.0e-8
        for component in project.par.glitches:
            if component.glep is None:
                continue
            glep = float(component.glep)
            if start <= glep <= finish:
                extra.extend([max(start, glep - eps), glep, min(finish, glep + eps)])
        if extra:
            base = np.unique(np.concatenate([base, np.asarray(extra, dtype=float)]))
        return base

    def compute(
        self,
        project: PulsarProject,
        include_glitches: bool = True,
        grid_points: int = 1200,
        toa_window_days: float = 30.0,
        compute_toa_series: bool = True,
        summarize_toas: bool = True,
    ) -> ModelResult:
        if project.par is None:
            raise ProjectNotComputableError("A PAR timing model is required for model computation.")
        key = self.cache.key(
            project, include_glitches, grid_points, toa_window_days,
            compute_toa_series, summarize_toas,
        )
        hit = self.cache.get(key)
        if hit is not None:
            return hit

        t0 = time.perf_counter()
        model = project.par
        active = None if project.active_components is None else set(project.active_components)
        mjd_grid = self.model_grid(project, grid_points)

        f0_noglit, f1_noglit, f2_noglit = compute_spin(model, mjd_grid, include_glitches=False, active_components=active)
        phase_noglit, phase_dot_noglit, phase_ddot_noglit = compute_phase_bundle(model, mjd_grid, include_glitches=False, active_components=active)

        f0_model, f1_model, f2_model = compute_spin(model, mjd_grid, include_glitches, active)
        phase, phase_dot, phase_ddot = compute_phase_bundle(model, mjd_grid, include_glitches, active)
        if len(phase):
            phase = phase - phase[0]
            phase_noglit = phase_noglit - phase_noglit[0]

        glitch_f0 = f0_model - f0_noglit
        glitch_f1 = f1_model - f1_noglit
        glitch_f2 = f2_model - f2_noglit
        glitch_phase = phase - phase_noglit

        obs = project.observations
        if obs is None:
            empty = np.array([], dtype=float)
            f0_data = f1_data = f2_data = empty
            r0 = empty
            r1 = r2 = None
            st0 = stats(empty)
            st1 = st2 = None
        else:
            f0_data, f1_data, f2_data = compute_spin(model, obs.mjd, include_glitches, active)
            r0 = residual(obs.f0, f0_data)
            r1 = residual(obs.f1, f1_data) if obs.f1 is not None else None
            r2 = residual(obs.f2, f2_data) if obs.f2 is not None else None
            st0 = stats(r0, obs.f0_err, dof=4)
            st1 = None if r1 is None else stats(r1, obs.f1_err, dof=4)
            st2 = None if r2 is None else stats(r2, obs.f2_err, dof=4)

        if project.toas is None or not compute_toa_series:
            toa_phase = np.array([], dtype=float)
            toa_frequency = np.array([], dtype=float)
        else:
            toa_phase = compute_phase(model, project.toas.mjd, include_glitches, active)
            toa_frequency, _, _ = compute_spin(model, project.toas.mjd, include_glitches, active)

        glitch_toa_summaries = (
            summarize_glitch_toas(model, project.toas, toa_window_days)
            if summarize_toas else ()
        )

        result = ModelResult(
            dataset_id=project.dataset_id,
            model_mjd=mjd_grid,
            f0_model=f0_model,
            f1_model=f1_model,
            f2_model=f2_model,
            f0_noglit=f0_noglit,
            f1_noglit=f1_noglit,
            f2_noglit=f2_noglit,
            phase=phase,
            phase_dot=phase_dot,
            phase_ddot=phase_ddot,
            phase_noglit=phase_noglit,
            phase_dot_noglit=phase_dot_noglit,
            phase_ddot_noglit=phase_ddot_noglit,
            glitch_f0=glitch_f0,
            glitch_f1=glitch_f1,
            glitch_f2=glitch_f2,
            glitch_phase=glitch_phase,
            f0_at_data=f0_data,
            f1_at_data=f1_data,
            f2_at_data=f2_data,
            residual_f0=r0,
            residual_f1=r1,
            residual_f2=r2,
            stats_f0=st0,
            stats_f1=st1,
            stats_f2=st2,
            toa_phase=toa_phase,
            toa_frequency=toa_frequency,
            glitch_groups=group_components_by_epoch(model.glitches),
            glitch_toa_summaries=glitch_toa_summaries,
            computed_seconds=float(time.perf_counter() - t0),
        )
        self.cache.set(key, result)
        return result
