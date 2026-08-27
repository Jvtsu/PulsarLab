from pulsarlab.datasets.loader import load_pair
from pulsarlab.parsers.dat_parser import parse_dat
from pulsarlab.parsers.par_parser import parse_par


def test_empty_dat_returns_error():
    obs, report = parse_dat("# empty\n")
    assert obs is None
    assert report.errors


def test_pepoch_invalid_rejected():
    model, report = parse_par("F0 1\nPEPOCH not-a-number\n")
    assert model is None
    assert report.errors


def test_no_observations_in_par_window():
    par = "F0 1\nPEPOCH 58000\nSTART 59000\nFINISH 59001\n"
    dat = "58000 1 1e-9\n58001 1 1e-9\n"
    ds, report = load_pair(par, dat)
    assert ds is None
    assert any("No observations" in e for e in report.errors)
