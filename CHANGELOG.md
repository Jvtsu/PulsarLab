# Changelog

All notable public changes to PulsarLab are documented in this file.

## 1.0.0 - 2026-08-09

First official public release of PulsarLab.

### Added

- Desktop application built with PySide6 and the `plab` command-line entry point.
- Independent loading of PAR, DAT and TIM files in any supported combination.
- Pulsar spin-evolution analysis using F0, F1, F2 and integrated rotational phase.
- Permanent and exponential glitch modelling, including multiple components at one epoch.
- Processed frequency residuals and TOA context analysis around glitch epochs.
- English and Spanish interface strings, dynamic messages and plotting labels.
- Project manager, residual analysis, glitch/TOA views and project summaries.
- Optional PINT/Astropy validation bridge and optional PyQtGraph plotting backend.
- Example PAR, DAT and TIM datasets.
- Automated test suite and GitHub Actions for Windows, Linux and macOS.
- Reproducible Windows desktop builds using PyInstaller and Inno Setup.

### Performance

- Cached scientific pipeline operations.
- Selective TOA-series and TOA-summary computation when a view does not require them.
- Display-only downsampling for very large Matplotlib datasets while preserving full scientific arrays.

### Packaging

- Package name standardized as `pulsarlab`.
- Public version reset to `1.0.0` for the first official release.
- Windows installer, portable executable and portable folder ZIP use release-neutral product naming.
