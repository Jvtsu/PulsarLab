import numpy as np

from pulsarlab.core.types import GlitchComponent, ParModel
from pulsarlab.core.spin_model import compute_spin
from pulsarlab.core.phase_model import compute_phase
from pulsarlab.core.glitch_model import delta_frequency, delta_frequency_derivative, delta_phase
from pulsarlab.core.units import SECONDS_PER_DAY


def make_model(**extra):
    params = {"F0": 10.0, "F1": -1e-10, "F2": 2e-21, "F3": 0.0, "PEPOCH": 58000.0}
    params.update(extra)
    return ParModel(params=params, glitches=())


def test_spin_polynomial_units_seconds():
    model = make_model()
    mjd = np.array([58000.0, 58001.0])
    f0, f1, f2 = compute_spin(model, mjd, include_glitches=False)
    t = SECONDS_PER_DAY
    assert np.isclose(f0[1], 10.0 - 1e-10 * t + 0.5 * 2e-21 * t**2)
    assert np.isclose(f1[1], -1e-10 + 2e-21 * t)
    assert np.isclose(f2[1], 2e-21)


def test_glitch_does_not_affect_before_epoch():
    g = GlitchComponent(index=1, glep=58010.0, glf0=1e-6)
    model = ParModel(params={"F0": 1.0, "PEPOCH": 58000.0}, glitches=(g,))
    f0, _, _ = compute_spin(model, np.array([58009.0, 58010.0]), include_glitches=True)
    assert np.isclose(f0[0], 1.0)
    assert np.isclose(f0[1], 1.0 + 1e-6)


def test_exponential_derivative_consistency():
    g = GlitchComponent(index=1, glep=58000.0, glf0d=2e-6, gltd=10.0)
    t = np.array([0.0, 5 * SECONDS_PER_DAY, 10 * SECONDS_PER_DAY])
    f = delta_frequency(g, t, 58000.0)
    fd = delta_frequency_derivative(g, t, 58000.0)
    tau = 10 * SECONDS_PER_DAY
    assert np.allclose(f, 2e-6 * np.exp(-t / tau))
    assert np.allclose(fd, -(2e-6 / tau) * np.exp(-t / tau))


def test_phase_integral_matches_frequency_numerically():
    g = GlitchComponent(index=1, glep=58000.0, glf0=1e-6, glf1=2e-15, glf0d=2e-6, gltd=4.0)
    t = np.linspace(0, 3 * SECONDS_PER_DAY, 10000)
    phase = delta_phase(g, t, 58000.0)
    numerical_freq = np.gradient(phase, t)
    freq = delta_frequency(g, t, 58000.0)
    assert np.max(np.abs(numerical_freq[10:-10] - freq[10:-10])) < 2e-10


def test_phase_derivative_matches_compute_spin_polynomial():
    model = make_model()
    mjd = np.linspace(58000, 58010, 2000)
    phase = compute_phase(model, mjd, include_glitches=False)
    t = (mjd - model.pepoch) * SECONDS_PER_DAY
    numerical = np.gradient(phase, t)
    f0, _, _ = compute_spin(model, mjd, include_glitches=False)
    assert np.max(np.abs(numerical[20:-20] - f0[20:-20])) < 1e-7
