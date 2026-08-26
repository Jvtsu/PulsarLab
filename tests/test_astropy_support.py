from __future__ import annotations

import numpy as np
import pytest

from pulsarlab.core.units import mjd_to_seconds, SECONDS_PER_DAY


def test_astropy_mjd_seconds_agrees_with_numpy():
    pytest.importorskip("astropy")
    from pulsarlab.core.astro_support import mjd_to_seconds_astropy, seconds_per_day_astropy

    mjd = np.array([58000.0, 58000.25, 58001.0, 58010.5])
    ref = 58000.0
    assert seconds_per_day_astropy() == pytest.approx(SECONDS_PER_DAY)
    assert np.allclose(mjd_to_seconds(mjd, ref), mjd_to_seconds_astropy(mjd, ref), rtol=0, atol=1e-9)


def test_astropy_coordinate_validation_warns_on_bad_coordinate():
    pytest.importorskip("astropy")
    from pulsarlab.parsers.par_parser import parse_par
    from pulsarlab.core.validation import validate_par_model

    model, report = parse_par("F0 10\nPEPOCH 58000\nRAJ not-a-ra\nDECJ +20:00:00\n")
    assert model is not None, report.errors
    warnings = validate_par_model(model).warnings
    assert any("Astropy could not parse RAJ/DECJ" in w for w in warnings)
