"""Programmatic scripts API used by CLI and tests."""

from __future__ import annotations

import numpy as np

from pulsarlab.core.glitch_model import delta_frequency, delta_phase
from pulsarlab.core.types import GlitchComponent
from pulsarlab.parsers.par_parser import parse_par
from pulsarlab.parsers.dat_parser import parse_dat
from pulsarlab.datasets.loader import load_pair
from pulsarlab.engine.pipeline import Pipeline


def run_selfcheck() -> None:
    par = """
PSRJ JTEST
F0 10.0
F1 -1D-10
F2 2D-21
PEPOCH 58000
START 58000
FINISH 58010
GLEP_1 58005
GLF0_1 1D-6
GLF0D_1 2D-6
GLTD_1 10
"""
    dat = """
# MJD F0 F0_ERR F1 F1_ERR
58000 10.0 1e-9 -100000 100
58005 9.999956800 1e-9 -100000 100
58010 9.999913600 1e-9 -100000 100
"""
    model, pr = parse_par(par)
    assert model is not None and pr.ok, pr
    obs, dr = parse_dat(dat)
    assert obs is not None and dr.ok, dr
    ds, rep = load_pair(par, dat, "synthetic.par", "synthetic.dat")
    assert ds is not None and not rep.errors, rep.errors
    res = Pipeline().compute(ds)
    assert res.f0_model.size > 0
    assert np.allclose(res.f0_model - res.f0_noglit, res.glitch_f0)
    assert np.allclose(res.phase - res.phase_noglit, res.glitch_phase)
    assert np.nanmax(np.abs(res.glitch_f0)) > 0
    g = GlitchComponent(index=1, glep=58000, glf0d=1e-6, gltd=1.0)
    t = np.array([0.0, 86400.0])
    assert np.isclose(delta_frequency(g, t, 58000)[0], 1e-6)
    assert np.isclose(delta_phase(g, t, 58000)[1], 1e-6 * 86400 * (1 - np.exp(-1)))
    print("PulsarLab self-check passed.")
