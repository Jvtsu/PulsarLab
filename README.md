# PulsarLab

*A desktop and headless scientific platform for pulsar spin evolution, glitch modelling, and TOA context analysis.*

**[Leer en español](README.es.md)**

![PulsarLab workspace](docs/assets/screenshot.png)

**Current public release: 1.0.0**

## Highlights

- Loads PAR, DAT, and TIM files **independently and in any order** — no need to have all three to start working.
- Computes spin evolution (F0, F1, F2), integrated phase, and permanent/exponential glitch terms from a TEMPO/TEMPO2-style timing model.
- Processed frequency residuals (observed − model) and TOA context analysis (counts, nearest arrival, uncertainty) around every glitch epoch.
- One command to check everything is working: `plab --selfcheck`.
- Optional cross-validation against `pint-pulsar` (PINT) when you want a second opinion on your results.
- Bilingual interface (English/Spanish) out of the box.

## Overview

PulsarLab is a scientific tool for working with pulsar timing data: fitting and inspecting a spin-evolution model, modelling glitches, computing processed frequency residuals, and putting TOA (Time of Arrival) data in context around glitch events. It runs as a PySide6 desktop application (`plab`) or headless, so the same computation core can be scripted or checked without opening a window.

The scientific core is intentionally NumPy-first and UI-free — the interface only renders numbers that the engine has already computed. An optional bridge to [PINT](https://github.com/nanograv/PINT) is available for independent cross-validation, but PulsarLab does not depend on it for day-to-day use.

### Author

Built and maintained by the PulsarLab team.

## Usage

Open an empty workspace:

```bash
plab
```

Load any initial combination, in any order:

```bash
plab model.par
plab observations.dat model.par
plab arrivals.tim model.par observations.dat
```

More files can be added from the interface once it's open. The command line accepts at most one initial file of each type.

Run a headless self-check (useful in CI or to confirm the install works, no window required):

```bash
plab --selfcheck
```

### Supported project combinations

| PAR | DAT | TIM | Result |
|---|---|---|---|
| Yes | No | No | Full model, phase, spin and glitch computation |
| No | Yes | No | Stored processed observations, not computable until PAR is attached |
| No | No | Yes | Stored and visualized TOAs, not computable until PAR is attached |
| Yes | Yes | No | Model plus processed frequency residuals |
| Yes | No | Yes | Model plus glitch and TOA context analysis |
| Yes | Yes | Yes | Complete workflow |

## Installation

Python 3.10 or newer is required. A virtual environment is recommended.

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-win.txt
pip install -e .
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-linux.txt
pip install -e .
```

A minimal Linux desktop may also need the Qt/XCB system libraries required by PySide6.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-macos.txt
pip install -e .
```

Use a native Python build matching the Mac architecture.

### Optional extras

Cross-validation against PINT (adds Astropy and `pint-pulsar` — validation bridges, not replacements for the NumPy-first production core):

```bash
pip install -r requirements-validation.txt
```

Faster optional plotting backend (PyQtGraph):

```bash
pip install -r requirements-fastplot.txt
```

This repository includes the desktop runtime **and** the development material: tests, scripts, documentation, examples, and packaging files. End users only need the installed application or the runtime dependencies; contributors can use the complete checkout for testing, validation, benchmarking, and desktop builds.

## Scientific scope

PulsarLab computes:

- F0, F1, F2, and integrated phase from a timing model.
- Permanent and exponential glitch terms after each GLEP, including multiple components sharing one epoch.
- Processed frequency residuals from DAT values as observed minus model.
- TOA phase and instantaneous model frequency at TIM epochs.
- TOA counts, before/after counts, nearest arrival, and uncertainty summaries around each physical glitch event.

PulsarLab does not claim that its nearest-pulse proxy is a full barycentric timing residual — PINT residuals are reported separately, through the optional validation bridge (`pulsarlab.validation_pint`, `compare_with_pint(par_path, tim_path)`), once `pint-pulsar` is installed.

### TIM format support

The parser supports the common TEMPO2 FORMAT 1 row:

```text
name frequency_MHz MJD uncertainty_us observatory [flags...]
```

Recognized numeric flags include `-pn` for pulse number and `-phase`/`-padd` for phase offset. Other flags are preserved as key/value pairs. Directives are retained as metadata; `INCLUDE` directives are reported but not expanded automatically. TOA uncertainties remain in microseconds in the parsed table — conversion to seconds is centralized in `pulsarlab/core/units.py`.

## Project layout

```text
pulsarlab/
  core/            physics, units, immutable scientific types
  parsers/         PAR, DAT and TIM parsing
  datasets/        optional-component projects and manager
  engine/          cached model, residual and TOA analysis
  visualization/   Matplotlib rendering only
  ui/              PySide6 application
  i18n/            English and Spanish interface strings
  cli/             command-line entry point
requirements*.txt  base, platform aliases and optional runtime tools
```

## Feedback and Contributing

Found a bug, a mistranslation, or something that doesn't match the physics? Please report it with steps to reproduce — that's the single most useful thing you can include. Suggestions on the interface, the Spanish translation, or the documentation are equally welcome.

## License

PulsarLab 1.0.0 is distributed under the rights notice in [`LICENSE`](LICENSE).
