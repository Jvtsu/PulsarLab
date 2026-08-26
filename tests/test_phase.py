import numpy as np

from pulsarlab.core.phase_model import compute_phase
from pulsarlab.core.spin_model import compute_spin
from pulsarlab.core.types import ParModel
from pulsarlab.core.units import SECONDS_PER_DAY


def test_phase_derivative_matches_frequency_away_from_edges():
    model = ParModel(params={"F0": 12.0, "F1": -1e-10, "F2": 2e-21, "PEPOCH": 58000.0})
    mjd = np.linspace(58000, 58002, 5000)
    phase = compute_phase(model, mjd)
    frequency, _, _ = compute_spin(model, mjd)
    numerical = np.gradient(phase, (mjd - mjd[0]) * SECONDS_PER_DAY, edge_order=2)
    assert np.allclose(numerical[10:-10], frequency[10:-10], rtol=0, atol=1e-8)
