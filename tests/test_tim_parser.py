from __future__ import annotations

import numpy as np

from pulsarlab.parsers.tim_parser import parse_tim


def test_format1_tim_parses_flags_and_sorts():
    text = """
FORMAT 1
late 1400 58002 3.0 @ -pn 20 -backend X
C comment
early 800 58000 2.0 ao -pn 10 -phase 0.25
middle 1000 58001 4.0 gb
"""
    toas, report = parse_tim(text, "x.tim")
    assert toas is not None, report.errors
    assert toas.n == 3
    assert np.all(np.diff(toas.mjd) > 0)
    assert report.directives_seen == 1
    assert any("sorted" in warning for warning in report.warnings)
    assert toas.row(0).pulse_number == 10
    assert toas.row(0).phase_offset == 0.25
    assert toas.row(2).flag_map["backend"] == "X"


def test_invalid_tim_lines_report_without_crashing():
    toas, report = parse_tim("FORMAT 1\nbad row\nx 1400 nope 2 @\n")
    assert toas is None
    assert report.errors
    assert report.invalid_toas == 2


def test_nonpositive_uncertainty_is_nan_and_warned():
    toas, report = parse_tim("FORMAT 1\nx 1400 58000 0 @\n")
    assert toas is not None
    assert np.isnan(toas.uncertainty_us[0])
    assert any("non-positive" in warning for warning in report.warnings)


def test_negative_numeric_flag_value_is_not_mistaken_for_new_flag():
    toas, report = parse_tim("FORMAT 1\nx 1400 58000 2 @ -phase -0.25 -pn -3\n")
    assert toas is not None, report.errors
    row = toas.row(0)
    assert row.phase_offset == -0.25
    assert row.pulse_number == -3
