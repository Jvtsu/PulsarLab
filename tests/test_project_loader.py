from __future__ import annotations

import pytest

from pulsarlab.datasets.loader import attach_component, load_project
from pulsarlab.engine.pipeline import Pipeline, ProjectNotComputableError

PAR = """
PSRJ JTEST
F0 10
F1 -1e-10
PEPOCH 58000
START 58000
FINISH 58010
GLEP_1 58005
GLF0_1 1e-6
"""
DAT = "58000 10 1e-9\n58005 9.99995 1e-9\n58010 9.9999 1e-9\n"
TIM = "FORMAT 1\na 1400 58004 2 @\nb 1400 58005.1 3 @\nc 1400 58007 4 @\n"


@pytest.mark.parametrize(
    "kwargs, has_par, has_dat, has_tim",
    [
        ({"par_source": PAR}, True, False, False),
        ({"dat_source": DAT}, False, True, False),
        ({"tim_source": TIM}, False, False, True),
        ({"par_source": PAR, "dat_source": DAT}, True, True, False),
        ({"par_source": PAR, "tim_source": TIM}, True, False, True),
        ({"par_source": PAR, "dat_source": DAT, "tim_source": TIM}, True, True, True),
    ],
)
def test_all_partial_project_combinations(kwargs, has_par, has_dat, has_tim):
    project, report = load_project(**kwargs)
    assert project is not None, report.errors
    assert project.has_model is has_par
    assert project.has_observations is has_dat
    assert project.has_toas is has_tim


def test_par_only_computes_without_dat():
    project, report = load_project(par_source=PAR)
    assert project is not None, report.errors
    result = Pipeline().compute(project, grid_points=128)
    assert result.model_mjd.size >= 128
    assert result.stats_f0.n == 0
    assert result.residual_f0.size == 0


def test_dat_only_is_storable_but_not_computable():
    project, report = load_project(dat_source=DAT)
    assert project is not None, report.errors
    with pytest.raises(ProjectNotComputableError):
        Pipeline().compute(project)


def test_attach_independent_components_preserves_project_identity():
    project, report = load_project(par_source=PAR, dataset_id="p1")
    assert project is not None, report.errors
    project2, report2 = attach_component(project, "tim", TIM, "x.tim")
    assert project2 is not None, report2.errors
    assert project2.dataset_id == "p1"
    assert project2.par is not None
    assert project2.toas is not None
    project3, report3 = attach_component(project2, "dat", DAT, "x.dat")
    assert project3 is not None, report3.errors
    assert project3.n_observations == 3
    assert project3.n_toas == 3


def test_signature_changes_when_toa_values_change():
    p1, _ = load_project(par_source=PAR, tim_source=TIM, dataset_id="same")
    p2, _ = load_project(par_source=PAR, tim_source=TIM.replace("58007", "58008"), dataset_id="same")
    assert p1 is not None and p2 is not None
    assert p1.scientific_signature() != p2.scientific_signature()


def test_toas_outside_model_interval_are_retained_with_warning():
    tim = "FORMAT 1\na 1400 57999 2 @\nb 1400 58005 2 @\nc 1400 58011 2 @\n"
    project, report = load_project(par_source=PAR, tim_source=tim)
    assert project is not None, report.errors
    assert project.n_toas == 3
    assert project.metadata["toas_outside_model_range"] == 2
    assert any("retained for context" in warning for warning in report.warnings)
