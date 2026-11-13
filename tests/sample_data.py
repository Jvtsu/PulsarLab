"""Small deterministic scientific inputs for tests.

The repository intentionally does not ship user PAR/DAT/TIM data. Tests build
synthetic, reproducible inputs in memory or in pytest's temporary directory.
"""

from __future__ import annotations

import math
from pathlib import Path


def sample_sources(
    *,
    psr: str = "J0537-6910",
    f0: float = 62.0,
    f1: float = -1.99e-10,
    f0_error: float = 2.0e-8,
    f1_error: float = 1.0e-17,
    noise_amplitude: float = 3.0e-8,
    with_glitch: bool = True,
    with_tim: bool = True,
) -> tuple[str, str, str | None]:
    """Return compact PAR, DAT, and optional TIM contents for regression tests."""
    pe = 58000.0
    glitch_epoch = 58050.0
    glitch_f0 = 1.5e-5 if with_glitch else 0.0
    glitch_f1 = 1.0e-14 if with_glitch else 0.0
    glitch_f0d = 2.0e-6 if with_glitch else 0.0
    glitch_tau_days = 10.0

    par_lines = [
        f"PSRJ {psr}",
        f"F0 {f0:.17g}",
        f"F1 {f1:.17g}",
        "F2 0",
        f"PEPOCH {pe:.1f}",
        "START 57999",
        "FINISH 58100",
    ]
    if with_glitch:
        par_lines.extend([
            f"GLEP_1 {glitch_epoch:.1f}",
            f"GLF0_1 {glitch_f0:.17g}",
            f"GLF1_1 {glitch_f1:.17g}",
            f"GLF0D_1 {glitch_f0d:.17g}",
            f"GLTD_1 {glitch_tau_days:.1f}",
        ])
    par_text = "\n".join(par_lines) + "\n"

    dat_rows = ["# MJD F0 F0_ERR F1 F1_ERR F2 F2_ERR"]
    for index in range(19):
        mjd = pe + index * 5.0
        dt_seconds = (mjd - pe) * 86400.0
        after_glitch = max(0.0, (mjd - glitch_epoch) * 86400.0)
        f0_model = f0 + f1 * dt_seconds
        f1_model = f1
        if with_glitch and mjd >= glitch_epoch:
            f0_model += glitch_f0 + glitch_f1 * after_glitch
            f0_model += glitch_f0d * math.exp(-after_glitch / (glitch_tau_days * 86400.0))
            f1_model += glitch_f1 - (
                glitch_f0d / (glitch_tau_days * 86400.0)
            ) * math.exp(-after_glitch / (glitch_tau_days * 86400.0))
        perturbation = noise_amplitude * math.sin(index * 1.17)
        f0_observed = f0_model + perturbation
        f1_observed = f1_model
        dat_rows.append(
            f"{mjd:.6f} {f0_observed:.17g} {f0_error:.17g} "
            f"{f1_observed:.17g} {f1_error:.17g} 0 1e-25"
        )
    dat_text = "\n".join(dat_rows) + "\n"

    tim_text: str | None = None
    if with_tim:
        tim_rows = ["FORMAT 1"]
        for index, mjd in enumerate((58045.0, 58048.0, 58049.5, 58050.5, 58052.0, 58055.0, 58060.0)):
            tim_rows.append(
                f"toa{index} 1400 {mjd:.6f} {2.0 + 0.2 * index:.3f} @ -pn {1000 + index}"
            )
        tim_text = "\n".join(tim_rows) + "\n"

    return par_text, dat_text, tim_text


def write_sample_files(
    directory: Path,
    *,
    prefix: str = "sample",
    **kwargs,
) -> tuple[Path, Path, Path | None]:
    """Write deterministic test inputs under a temporary directory."""
    directory.mkdir(parents=True, exist_ok=True)
    par_text, dat_text, tim_text = sample_sources(**kwargs)
    par_path = directory / f"{prefix}.par"
    dat_path = directory / f"{prefix}.dat"
    tim_path = directory / f"{prefix}.tim" if tim_text is not None else None
    par_path.write_text(par_text, encoding="utf-8")
    dat_path.write_text(dat_text, encoding="utf-8")
    if tim_path is not None and tim_text is not None:
        tim_path.write_text(tim_text, encoding="utf-8")
    return par_path, dat_path, tim_path
