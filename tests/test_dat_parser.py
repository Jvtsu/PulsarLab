import numpy as np

from pulsarlab.parsers.dat_parser import parse_dat


def test_positional_minimal_dat():
    obs, report = parse_dat("58000 10 1e-9\n58001 9.9 1e-9\n")
    assert obs is not None, report.errors
    assert obs.n == 2
    assert np.all(np.diff(obs.mjd) > 0)


def test_header_and_display_unit_scaling():
    text = """
# MJD F0 F0_ERR F1 F1_ERR F2 F2_ERR
58000 10 1e-9 -100000 100 42 2
58001 9.9 1e-9 -100001 100 43 2
"""
    obs, report = parse_dat(text)
    assert obs is not None, report.errors
    assert report.scaled_f1
    assert report.scaled_f2
    assert obs.f1 is not None
    assert obs.f2 is not None
    assert np.isclose(obs.f1[0], -100000e-15)
    assert np.isclose(obs.f2[0], 42e-24)


def test_corrupt_lines_are_skipped():
    text = "header garbage\n58000 10 1e-9 trailing ok\nnot numeric\n58001 9.9 1e-9\n"
    obs, report = parse_dat(text)
    assert obs is not None
    assert obs.n == 2
    assert report.skipped_lines >= 1


def test_nonfinite_rows_dropped_and_negative_uncertainty_warns():
    text = "58000 10 -1e-9\n58001 nan 1e-9\n58002 9.8 1e-9\n"
    obs, report = parse_dat(text)
    assert obs is not None
    assert obs.n == 2
    assert any("non-positive" in w for w in report.warnings)
