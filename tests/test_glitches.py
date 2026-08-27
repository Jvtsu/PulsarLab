import numpy as np

from pulsarlab.core.glitch_model import sum_glitches
from pulsarlab.core.types import GlitchComponent
from pulsarlab.core.units import SECONDS_PER_DAY


def test_multiple_components_at_same_epoch_sum_without_interference():
    components = (
        GlitchComponent(index=1, glep=58001, glf0=1e-6),
        GlitchComponent(index=2, glep=58001, glf0=2e-6, glf0d=3e-6, gltd=2),
    )
    t = np.array([0.5, 1.0, 2.0]) * SECONDS_PER_DAY
    delta = sum_glitches(components, t, 58000.0, "f0")
    assert delta[0] == 0
    assert np.isclose(delta[1], 6e-6)
    expected = 3e-6 + 3e-6 * np.exp(-0.5)
    assert np.isclose(delta[2], expected)
