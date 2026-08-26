import numpy as np

from pulsarlab.core.units import microseconds_to_seconds, seconds_to_microseconds


def test_microsecond_conversion_roundtrip():
    values = np.array([0.5, 1.0, 1234.5])
    seconds = microseconds_to_seconds(values)
    assert np.allclose(seconds, values * 1e-6)
    assert np.allclose(seconds_to_microseconds(seconds), values)
