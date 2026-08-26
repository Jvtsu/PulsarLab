
import numpy as np

from pulsarlab.core.types import GlitchComponent, ParModel, ObservationTable
from pulsarlab.datasets.dataset import Dataset
from pulsarlab.engine.pipeline import Pipeline
from pulsarlab.core.units import SECONDS_PER_DAY


def make_dataset():
    g = GlitchComponent(index=1, glep=58005.0, glf0=1e-6, glf1=2e-15, glf0d=3e-6, gltd=10.0)
    par = ParModel(params={"PSRJ":"JTEST", "F0":10.0, "F1":-1e-10, "PEPOCH":58000.0, "START":58000.0, "FINISH":58020.0}, glitches=(g,))
    mjd = np.linspace(58000, 58020, 80)
    f0 = np.full_like(mjd, 10.0)
    err = np.full_like(mjd, 1e-9)
    obs = ObservationTable(mjd=mjd, f0=f0, f0_err=err)
    return Dataset(dataset_id="d1", name="synthetic", par=par, observations=obs, metadata={"model_start":58000.0, "model_finish":58020.0})


def test_pipeline_exposes_glitch_contribution_arrays():
    ds = make_dataset()
    res = Pipeline().compute(ds, grid_points=200)
    assert res.glitch_f0.shape == res.model_mjd.shape
    assert res.glitch_f1.shape == res.model_mjd.shape
    assert res.glitch_phase.shape == res.model_mjd.shape
    assert np.allclose(res.f0_model - res.f0_noglit, res.glitch_f0)
    assert np.allclose(res.f1_model - res.f1_noglit, res.glitch_f1)
    assert np.allclose(res.phase - res.phase_noglit, res.glitch_phase)


def test_glitch_contribution_is_zero_before_epoch_and_nonzero_after():
    ds = make_dataset()
    res = Pipeline().compute(ds, grid_points=200)
    before = res.model_mjd < 58005.0
    after = res.model_mjd >= 58005.0
    assert np.allclose(res.glitch_f0[before], 0.0)
    assert np.max(np.abs(res.glitch_f0[after])) > 0.0


def test_transient_phase_contains_one_minus_exp_integral_at_epoch_plus_tau():
    ds = make_dataset()
    res = Pipeline().compute(ds, grid_points=200)
    target = 58015.0  # glep + GLTD, so dt=tau
    idx = int(np.argmin(np.abs(res.model_mjd - target)))
    dt = (res.model_mjd[idx] - 58005.0) * SECONDS_PER_DAY
    tau = 10.0 * SECONDS_PER_DAY
    expected_transient_phase = 3e-6 * tau * (1.0 - np.exp(-dt / tau))
    expected_perm = 1e-6 * dt + 0.5 * 2e-15 * dt**2
    assert np.isclose(res.glitch_phase[idx], expected_perm + expected_transient_phase, rtol=1e-4, atol=1e-4)
