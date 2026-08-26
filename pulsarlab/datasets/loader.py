"""Load and incrementally assemble PulsarLab projects."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
import uuid

import numpy as np

from pulsarlab.core.types import ObservationTable, ParModel, TOATable
from pulsarlab.core.validation import validate_observations, validate_par_model, validate_toas
from pulsarlab.datasets.dataset import PulsarProject
from pulsarlab.parsers.dat_parser import parse_dat
from pulsarlab.parsers.par_parser import parse_par
from pulsarlab.parsers.reports import Report
from pulsarlab.parsers.tim_parser import parse_tim

ComponentKind = Literal["par", "dat", "tim"]


def _stem(filename: str | None, fallback: str) -> str:
    return Path(filename or fallback).stem


def _name_from_files(par_name: str | None = None, dat_name: str | None = None, tim_name: str | None = None) -> str:
    stems = []
    for filename, fallback in ((par_name, "model.par"), (dat_name, "data.dat"), (tim_name, "toas.tim")):
        if filename:
            stems.append(_stem(filename, fallback))
    if not stems:
        return "Untitled project"
    if len(set(stems)) == 1:
        return stems[0]
    return "/".join(stems)


def _validity_bounds(model: ParModel) -> tuple[float | None, float | None]:
    start, finish = model.start, model.finish
    if start is not None and finish is not None and start > finish:
        return finish, start
    return start, finish


def _filter_observations_to_model(
    model: ParModel,
    observations: ObservationTable,
    report: Report,
) -> tuple[ObservationTable | None, dict]:
    start, finish = _validity_bounds(model)
    dat_start, dat_finish = observations.mjd_span
    eff_start = start if start is not None else dat_start
    eff_finish = finish if finish is not None else dat_finish
    filtered = observations.filtered_by_mjd(eff_start, eff_finish)
    if filtered.n == 0:
        report.errors.append(
            f"No observations fall inside the model interval [{eff_start:.6g}, {eff_finish:.6g}] MJD."
        )
        return None, {}
    if filtered.n != observations.n:
        report.warnings.append(f"Filtered observations to .par validity interval: kept {filtered.n}/{observations.n} rows.")
    if start is None and finish is None:
        report.warnings.append("No START/FINISH in .par; using loaded .dat span as model interval.")
    return filtered, {
        "model_start": eff_start,
        "model_finish": eff_finish,
        "dat_start": dat_start,
        "dat_finish": dat_finish,
    }


def _assemble_project(
    *,
    par: ParModel | None,
    observations: ObservationTable | None,
    toas: TOATable | None,
    report: Report,
    par_filename: str | None = None,
    dat_filename: str | None = None,
    tim_filename: str | None = None,
    display_name: str | None = None,
    dataset_id: str | None = None,
    existing_name: str | None = None,
    existing_metadata: dict | None = None,
) -> PulsarProject | None:
    metadata = dict(existing_metadata or {})
    if par is not None:
        report.extend(validate_par_model(par))
        metadata["par_filename"] = par_filename or par.source_name
    if observations is not None:
        report.extend(validate_observations(observations))
        metadata["dat_filename"] = dat_filename or observations.source_name
    if toas is not None:
        report.extend(validate_toas(toas))
        metadata["tim_filename"] = tim_filename or toas.source_name
    if report.errors:
        return None

    if par is not None and observations is not None:
        observations, interval_meta = _filter_observations_to_model(par, observations, report)
        if observations is None or report.errors:
            return None
        metadata.update(interval_meta)
    elif par is not None:
        start, finish = _validity_bounds(par)
        if start is not None:
            metadata["model_start"] = start
        if finish is not None:
            metadata["model_finish"] = finish
        if start is None and finish is None:
            report.warnings.append("No START/FINISH in .par; using TIM span or a PEPOCH-centered fallback interval.")

    if toas is not None:
        metadata.update({"tim_start": toas.mjd_span[0], "tim_finish": toas.mjd_span[1]})
        if par is not None and (par.start is not None or par.finish is not None):
            lo = float("-inf") if par.start is None else float(par.start)
            hi = float("inf") if par.finish is None else float(par.finish)
            if lo > hi:
                lo, hi = hi, lo
            inside = (toas.mjd >= lo) & (toas.mjd <= hi)
            outside_count = int(np.sum(~inside))
            metadata["toas_inside_model_range"] = int(np.sum(inside))
            metadata["toas_outside_model_range"] = outside_count
            if outside_count:
                report.warnings.append(
                    f"{outside_count}/{toas.n} TOAs fall outside the .par START/FINISH interval; retained for context."
                )

    name = display_name or existing_name or _name_from_files(par_filename, dat_filename, tim_filename)
    return PulsarProject(
        dataset_id=dataset_id or str(uuid.uuid4())[:8],
        name=name,
        par=par,
        observations=observations,
        toas=toas,
        metadata=metadata,
    )


def load_project(
    *,
    par_source=None,
    dat_source=None,
    tim_source=None,
    par_filename: str = "model.par",
    dat_filename: str = "data.dat",
    tim_filename: str = "toas.tim",
    display_name: str | None = None,
    dataset_id: str | None = None,
) -> tuple[PulsarProject | None, Report]:
    """Create a project from any non-empty PAR/DAT/TIM combination."""
    report = Report()
    if par_source is None and dat_source is None and tim_source is None:
        report.errors.append("At least one PAR, DAT, or TIM source is required.")
        return None, report

    par = None
    observations = None
    toas = None
    if par_source is not None:
        par, parsed = parse_par(par_source, par_filename)
        report.extend(parsed)
    if dat_source is not None:
        observations, parsed = parse_dat(dat_source, dat_filename)
        report.extend(parsed)
    if tim_source is not None:
        toas, parsed = parse_tim(tim_source, tim_filename)
        report.extend(parsed)
    if report.errors:
        return None, report

    return _assemble_project(
        par=par,
        observations=observations,
        toas=toas,
        report=report,
        par_filename=par_filename if par_source is not None else None,
        dat_filename=dat_filename if dat_source is not None else None,
        tim_filename=tim_filename if tim_source is not None else None,
        display_name=display_name,
        dataset_id=dataset_id,
    ), report


def attach_component(
    project: PulsarProject,
    kind: ComponentKind,
    source,
    filename: str | None = None,
) -> tuple[PulsarProject | None, Report]:
    """Return a replacement project after parsing one independently loaded file."""
    kind = kind.lower()  # type: ignore[assignment]
    report = Report()
    par, observations, toas = project.par, project.observations, project.toas
    par_filename = project.metadata.get("par_filename")
    dat_filename = project.metadata.get("dat_filename")
    tim_filename = project.metadata.get("tim_filename")

    if kind == "par":
        par_filename = filename or "model.par"
        par, parsed = parse_par(source, par_filename)
    elif kind == "dat":
        dat_filename = filename or "data.dat"
        observations, parsed = parse_dat(source, dat_filename)
    elif kind == "tim":
        tim_filename = filename or "toas.tim"
        toas, parsed = parse_tim(source, tim_filename)
    else:
        report.errors.append(f"Unsupported project component: {kind!r}.")
        return None, report
    report.extend(parsed)
    if report.errors:
        return None, report

    assembled = _assemble_project(
        par=par,
        observations=observations,
        toas=toas,
        report=report,
        par_filename=par_filename,
        dat_filename=dat_filename,
        tim_filename=tim_filename,
        dataset_id=project.dataset_id,
        existing_name=project.name,
        existing_metadata=project.metadata,
    )
    if assembled is not None:
        assembled = PulsarProject(
            dataset_id=assembled.dataset_id,
            name=assembled.name,
            par=assembled.par,
            observations=assembled.observations,
            toas=assembled.toas,
            visible=project.visible,
            active_components=project.active_components,
            metadata=assembled.metadata,
        )
    return assembled, report


def load_pair(
    par_source,
    dat_source,
    par_filename: str = "model.par",
    dat_filename: str = "data.dat",
    display_name: str | None = None,
    dataset_id: str | None = None,
) -> tuple[PulsarProject | None, Report]:
    """Backward-compatible loader for a PAR+DAT pair."""
    return load_project(
        par_source=par_source,
        dat_source=dat_source,
        par_filename=par_filename,
        dat_filename=dat_filename,
        display_name=display_name,
        dataset_id=dataset_id,
    )


def load_par(source, filename: str = "model.par", **kwargs) -> tuple[PulsarProject | None, Report]:
    return load_project(par_source=source, par_filename=filename, **kwargs)


def load_dat(source, filename: str = "data.dat", **kwargs) -> tuple[PulsarProject | None, Report]:
    return load_project(dat_source=source, dat_filename=filename, **kwargs)


def load_tim(source, filename: str = "toas.tim", **kwargs) -> tuple[PulsarProject | None, Report]:
    return load_project(tim_source=source, tim_filename=filename, **kwargs)
