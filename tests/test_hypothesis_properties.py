from __future__ import annotations

import numpy as np
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st

from pulsarlab.core.glitch_model import delta_frequency, delta_phase
from pulsarlab.core.types import GlitchComponent
from pulsarlab.core.units import SECONDS_PER_DAY


finite_small = st.floats(min_value=-1e-5, max_value=1e-5, allow_nan=False, allow_infinity=False)
positive_days = st.floats(min_value=1e-4, max_value=500.0, allow_nan=False, allow_infinity=False)


@given(glf0=finite_small, glf1=st.floats(min_value=-1e-15, max_value=1e-15, allow_nan=False, allow_infinity=False))
@settings(max_examples=120, deadline=None)
def test_glitch_zero_before_epoch_property(glf0: float, glf1: float):
    g = GlitchComponent(index=1, glep=58010.0, glf0=glf0, glf1=glf1)
    t = np.linspace(0, 9.999 * SECONDS_PER_DAY, 50)  # before GLEP relative to PEPOCH=58000
    assert np.all(delta_frequency(g, t, 58000.0) == 0.0)
    assert np.all(delta_phase(g, t, 58000.0) == 0.0)


@given(glf0d=finite_small.filter(lambda x: abs(x) > 1e-12), tau_days=positive_days)
@settings(max_examples=100, deadline=None)
def test_transient_phase_derivative_matches_frequency_property(glf0d: float, tau_days: float):
    g = GlitchComponent(index=1, glep=58000.0, glf0d=glf0d, gltd=tau_days)
    t = np.linspace(0, min(10 * tau_days * SECONDS_PER_DAY, 3e7), 5000)
    phase = delta_phase(g, t, 58000.0)
    freq = delta_frequency(g, t, 58000.0)
    numeric = np.gradient(phase, t)
    assert np.nanmax(np.abs(numeric[20:-20] - freq[20:-20])) < max(1e-9, abs(glf0d) * 1e-3)
