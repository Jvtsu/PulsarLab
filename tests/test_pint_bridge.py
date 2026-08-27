from __future__ import annotations

import pytest

from pulsarlab.parsers.par_parser import parse_par
from pulsarlab.validation_pint import check_par_with_pint, pint_available


def test_pint_bridge_reports_missing_or_load_status():
    model, report = parse_par("PSRJ J0000+0000\nF0 10\nF1 -1e-10\nPEPOCH 58000\n")
    assert model is not None, report.errors
    result = check_par_with_pint(model)
    if not pint_available():
        assert not result.available
        assert "not installed" in result.message
    else:
        assert result.available
        # PINT may reject simplified spin-only demo par files; that is useful validation info.
        assert isinstance(result.message, str) and result.message


def test_pint_can_be_imported_when_optional_dependency_present():
    if not pint_available():
        pytest.skip("pint-pulsar is not installed")
    from pint.models import get_model  # noqa: F401


def test_numerical_pint_bridge_contract_with_fake_backend(tmp_path, monkeypatch):
    import numpy as np
    import pulsarlab.validation_pint as bridge

    par_path = tmp_path / "model.par"
    tim_path = tmp_path / "toas.tim"
    par_path.write_text("F0 10\nPEPOCH 58000\nSTART 58000\nFINISH 58001\n")
    tim_path.write_text("FORMAT 1\na 1400 58000 2 @\nb 1400 58000.1 2 @\n")

    class Values:
        def __init__(self, values):
            self.value = np.asarray(values, dtype=float)

        def to_value(self, unit):
            return self.value

    class Phase:
        def __init__(self, values):
            values = np.asarray(values, dtype=float)
            self.int = Values(np.floor(values))
            self.frac = Values(values - np.floor(values))

    class FakeModel:
        def phase(self, toas, abs_phase=False):
            return Phase([0.0, 86400.0])

        def d_phase_d_toa(self, toas):
            return Values([10.0, 10.0])

        def __str__(self):
            return "Fake PINT model"

    class FakeTOAs:
        table = {"mjd_float": np.array([58000.0, 58000.1])}

    class FakeResiduals:
        def __init__(self, toas, model, subtract_mean=True):
            self.time_resids = Values([0.0, 0.0])

    monkeypatch.setattr(
        bridge,
        "_import_pint",
        lambda: (lambda path: FakeModel(), lambda path, model, usepickle=False: FakeTOAs(), FakeResiduals, None),
    )
    result = bridge.compare_with_pint(par_path, tim_path)
    assert result.ok
    assert result.n_toas == 2
    assert result.phase_max_abs_cycles is not None
    assert result.frequency_max_abs_hz is not None
    assert result.phase_max_abs_cycles < 1e-5
    assert result.frequency_max_abs_hz < 1e-12
    assert result.pint_residual_rms_seconds == 0.0
