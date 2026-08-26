from pulsarlab.i18n.dynamic_messages import localize_message, localize_messages


def test_dynamic_messages_translate_known_warnings_to_spanish():
    assert localize_message("F1 appears to be in display units; converted by 1e-15 to Hz/s.", "es") == "F1 parece estar en unidades de visualización; se convirtió por 1e-15 a Hz/s."
    assert localize_message("Some F2 uncertainties are non-positive; weighted statistics may ignore them.", "es").startswith("Algunas incertidumbres de F2")


def test_dynamic_messages_translate_parameterized_warnings_to_spanish():
    assert localize_message("Filtered observations to .par validity interval: kept 40/156 rows.", "es") == "Se filtraron observaciones al intervalo válido del .par: se conservaron 40/156 filas."
    assert localize_message("Dropped 3 row(s) with non-finite MJD/F0/F0 uncertainty.", "es") == "Se descartaron 3 fila(s) con MJD/F0/incertidumbre F0 no finitos."


def test_dynamic_messages_leave_english_and_unknown_unchanged():
    msg = "Custom scientific warning"
    assert localize_message(msg, "en") == msg
    assert localize_messages([msg], "es") == [msg]


def _assert_all_translated(warnings: list[str]) -> None:
    """Every warning a real parser/loader call produced must have a Spanish
    translation registered in dynamic_messages.py (literal or regex).

    This drives the check from the actual message-producing code instead of
    hardcoded copies of the strings, so a future wording change that isn't
    mirrored in the translation table fails here immediately rather than
    silently showing English text inside the Spanish UI (this is exactly how
    the TIM INCLUDE/FORMAT/out-of-range messages were found untranslated
    during a previous verification pass).
    """
    for w in warnings:
        es = localize_message(w, "es")
        assert es != w, f"No Spanish translation registered for runtime message: {w!r}"


def test_tim_parser_directive_and_edge_case_warnings_are_all_translated():
    from pulsarlab.parsers.tim_parser import parse_tim

    text = "\n".join([
        "FORMAT 2",
        "INCLUDE other.tim",
        "toa1 1400.0 58000.0 -1.0 @",
    ])
    table, report = parse_tim(text, "edge.tim")
    assert table is not None, report.errors
    assert report.warnings  # sanity: this file actually produced warnings
    _assert_all_translated(report.warnings)


def test_validate_toas_edge_case_warnings_are_all_translated():
    import numpy as np
    from pulsarlab.core.types import TOATable
    from pulsarlab.core.validation import validate_toas

    toas = TOATable(
        mjd=np.array([58001.0, 58000.0]),
        uncertainty_us=np.array([float("nan"), -1.0]),
        frequency_mhz=np.array([1400.0, float("nan")]),
        names=("a", "b"),
        observatories=("@", "@"),
    )
    report = validate_toas(toas)
    assert report.warnings
    _assert_all_translated(report.warnings)


def test_loader_toas_outside_par_range_warning_is_translated():
    from pulsarlab.datasets.loader import load_project

    par = "PSRJ J0000+0000\nF0 10\nPEPOCH 58000\nSTART 58000\nFINISH 58010\n"
    tim = "FORMAT 1\n" + "\n".join(
        f"toa{i} 1400.0 {mjd:.3f} 1.0 @" for i, mjd in enumerate([58005.0, 59000.0])
    )
    project, report = load_project(par_source=par, tim_source=tim, par_filename="p.par", tim_filename="t.tim")
    assert project is not None, report.errors
    assert any("outside the .par" in w for w in report.warnings)
    _assert_all_translated(report.warnings)


def test_validate_par_model_edge_case_warnings_are_all_translated():
    from pulsarlab.core.types import GlitchComponent, ParModel
    from pulsarlab.core.validation import validate_par_model

    model = ParModel(
        params={"F0": 10.0, "F1": -1.0, "PEPOCH": 58000.0, "START": 58010.0, "FINISH": 58000.0},
        glitches=(
            GlitchComponent(index=1, glep=None),
            GlitchComponent(index=2, glep=58005.0, gltd=-1.0),
            GlitchComponent(index=3, glep=58005.0, glf0=50.0),
        ),
    )
    report = validate_par_model(model)
    assert report.warnings
    _assert_all_translated(report.warnings)


def test_validate_observations_edge_case_warnings_are_all_translated():
    import numpy as np
    from pulsarlab.core.types import ObservationTable
    from pulsarlab.core.validation import validate_observations

    obs = ObservationTable(
        mjd=np.array([58001.0, 58000.0]),
        f0=np.array([10.0, 10.0]),
        f0_err=np.array([-1.0, -1.0]),
        f1=np.array([1.0, 1.0]),
    )
    report = validate_observations(obs)
    assert report.warnings
    _assert_all_translated(report.warnings)
