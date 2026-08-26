from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pulsarlab.parsers.par_parser import parse_par
from pulsarlab.validation_pint import check_par_with_pint, compare_with_pint


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a PAR and optionally compare PAR+TIM numerically with PINT.")
    parser.add_argument("par", type=pathlib.Path)
    parser.add_argument("tim", type=pathlib.Path, nargs="?")
    args = parser.parse_args()

    model, report = parse_par(args.par, args.par.name)
    if report.errors:
        print("PulsarLab parser errors:")
        for error in report.errors:
            print(" -", error)
        return 2
    print(f"PulsarLab parsed {args.par.name}: {report.glitches_found} glitch components")
    for warning in report.warnings:
        print(" - warning:", warning)

    if args.tim is None:
        result = check_par_with_pint(model)
        print(result.message)
        if result.model_summary:
            print(result.model_summary)
        return 0 if (not result.available or result.ok) else 1

    result = compare_with_pint(args.par, args.tim)
    print(result.message)
    if result.ok:
        print(f"TOAs: {result.n_toas}")
        print(f"max |Δphase| after constant-offset removal: {result.phase_max_abs_cycles:.6e} cycles")
        print(f"max |Δfrequency|: {result.frequency_max_abs_hz:.6e} Hz")
        print(f"PINT residual RMS: {result.pint_residual_rms_seconds:.6e} s")
        print(f"PulsarLab nearest-pulse proxy RMS: {result.pulsarlab_proxy_rms_seconds:.6e} s")
    return 0 if (not result.available or result.ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
