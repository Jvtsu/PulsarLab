"""Physics/data validators used before engine computations."""

from __future__ import annotations

import numpy as np

from pulsarlab.core.types import ObservationTable, ParModel, TOATable
from pulsarlab.parsers.reports import Report
from pulsarlab.core.astro_support import parse_skycoord_from_par, validate_mjd_with_astropy


def validate_par_model(model: ParModel) -> Report:
    report = Report()
    if not np.isfinite(model.f0) or model.f0 <= 0:
        report.errors.append("F0 must be a positive finite spin frequency.")
    if not np.isfinite(model.pepoch):
        report.errors.append("PEPOCH must be finite.")
    ok_mjd, mjd_msg = validate_mjd_with_astropy([model.pepoch] + [x for x in (model.start, model.finish) if x is not None])
    if not ok_mjd:
        report.warnings.append(mjd_msg)
    _coord, coord_warning = parse_skycoord_from_par(model.params)
    if coord_warning:
        report.warnings.append(coord_warning)
    if abs(model.f1) > 1e-5:
        report.warnings.append("|F1| is unusually large for a pulsar spin-down model; check units.")
    if model.start is not None and model.finish is not None and model.start > model.finish:
        report.warnings.append("START is greater than FINISH; PulsarLab will internally swap the interval.")
    for comp in model.glitches:
        if not comp.has_epoch:
            report.warnings.append(f"Glitch component {comp.index} has no epoch and will not affect the model.")
        if comp.gltd is not None and comp.gltd <= 0:
            report.warnings.append(f"Glitch component {comp.index} has non-positive GLTD; transient recovery ignored.")
        if abs(comp.glf0) > model.f0:
            report.warnings.append(f"Glitch component {comp.index} has GLF0 comparable to/larger than F0; check units.")
    return report


def validate_observations(obs: ObservationTable) -> Report:
    report = Report()
    if obs.n == 0:
        report.errors.append("Observation table is empty.")
        return report
    for name in ("mjd", "f0", "f0_err"):
        arr = np.asarray(getattr(obs, name), dtype=float)
        if not np.any(np.isfinite(arr)):
            report.errors.append(f"Column {name} contains no finite values.")
    ok_mjd, mjd_msg = validate_mjd_with_astropy(obs.mjd)
    if not ok_mjd:
        report.warnings.append(mjd_msg)
    if np.any(np.diff(obs.mjd) < 0):
        report.warnings.append("MJD values are not sorted; parser should sort them before analysis.")
    if np.nanmedian(obs.f0_err) <= 0:
        report.warnings.append("Typical F0 uncertainty is non-positive; weighted diagnostics may be disabled.")
    if obs.f1 is not None and np.nanmedian(np.abs(obs.f1)) > 1e-5:
        report.warnings.append("F1 values look too large for Hz/s; check whether display-unit scaling was missed.")
    return report


def validate_toas(toas: TOATable) -> Report:
    """Validate parsed TOAs without pretending to perform barycentric timing."""
    report = Report()
    if toas.n == 0:
        report.errors.append("TOA table is empty.")
        return report
    mjd = np.asarray(toas.mjd, dtype=float)
    sigma = np.asarray(toas.uncertainty_us, dtype=float)
    freq = np.asarray(toas.frequency_mhz, dtype=float)
    if not np.all(np.isfinite(mjd)):
        report.errors.append("TOA MJD column contains non-finite values.")
    if not np.any(np.isfinite(sigma) & (sigma > 0)):
        report.warnings.append("TOA table contains no positive finite uncertainties.")
    if np.any(np.isfinite(sigma) & (sigma <= 0)):
        report.warnings.append("Some TOA uncertainties are non-positive and will be ignored in error summaries.")
    if not np.all(np.isfinite(freq)):
        report.warnings.append("Some TOA observing frequencies are non-finite.")
    if np.any(np.diff(mjd) < 0):
        report.warnings.append("TOAs are not sorted by MJD; parser should sort them before analysis.")
    ok_mjd, mjd_msg = validate_mjd_with_astropy(mjd)
    if not ok_mjd:
        report.warnings.append(mjd_msg)
    return report
