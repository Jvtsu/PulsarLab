from pulsarlab.parsers.par_parser import parse_par, parse_float_token, serialize_par


def test_fortran_exponents_and_glitch_grouping():
    text = """
PSRJ J0000+0000
F0 10.0D0
F1 -1.0D-10
F2 2.0D-21
PEPOCH 58000
GLEP_1 58010
GLF0_1 1D-6
GLEP_2 58010
GLF0D_2 2D-6
GLTD_2 5
"""
    model, report = parse_par(text)
    assert model is not None, report.errors
    assert report.ok
    assert model.f0 == 10.0
    assert model.f1 == -1e-10
    assert len(model.glitches) == 2
    assert model.glitches[1].has_transient


def test_missing_required_params_errors():
    model, report = parse_par("PSRJ JX\nF1 -1e-10\n")
    assert model is None
    assert any("F0" in e for e in report.errors)
    assert any("PEPOCH" in e for e in report.errors)


def test_nonpositive_gltd_warns_and_disables():
    model, report = parse_par("F0 1\nPEPOCH 58000\nGLEP_1 58001\nGLF0D_1 1e-6\nGLTD_1 -1\n")
    assert model is not None
    assert model.glitches[0].gltd is None
    assert report.warnings


def test_serialize_roundtrip_basic():
    model, report = parse_par("F0 1\nPEPOCH 58000\nGLEP_1 58001\nGLF0_1 1e-6\n")
    assert model is not None
    text = serialize_par(model)
    model2, report2 = parse_par(text)
    assert model2 is not None
    assert model2.f0 == model.f0
    assert len(model2.glitches) == 1


def test_parse_float_rejects_nonfinite():
    import pytest
    with pytest.raises(ValueError):
        parse_float_token("nan")
