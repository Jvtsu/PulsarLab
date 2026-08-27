import numpy as np

from pulsarlab.core.spin_model import spin_polynomial
from pulsarlab.core.types import ParModel
from pulsarlab.core.units import SECONDS_PER_DAY


def test_spin_taylor_polynomial_uses_seconds():
    model = ParModel(params={"F0": 10.0, "F1": -2e-10, "F2": 3e-20, "F3": 4e-30, "PEPOCH": 58000.0})
    mjd = np.array([58000.0, 58001.0])
    f0, f1, f2 = spin_polynomial(model, mjd)
    t = SECONDS_PER_DAY
    assert np.isclose(f0[1], 10.0 - 2e-10*t + 0.5*3e-20*t**2 + (1/6)*4e-30*t**3)
    assert np.isclose(f1[1], -2e-10 + 3e-20*t + 0.5*4e-30*t**2)
    assert np.isclose(f2[1], 3e-20 + 4e-30*t)
