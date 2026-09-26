# Analytical Reports

This directory contains reproducible analytical, diagnostic, and historical
research outputs generated during development of the yield-curve
implementation.

It is not the operational curve-delivery mechanism. The current operational
snapshot belongs under `outputs/baseline/`.

## Structure

- `figures/` — rendered analytical figures.
- `tables/` — machine-readable CSV outputs used in reports and figures.
- `text/` — human-readable console-style reports.
- `metadata/` — experiment configuration and execution metadata.

## Data classification

Outputs generated from the current reference experiment are based on
synthetic F-TIIE OIS quotes and must not be interpreted as observed
market data.

## Reproducibility

All artifacts in this directory should be reproducible from the scripts
under `scripts/`.

For computationally expensive experiments, the underlying plotted
series are also persisted as CSV so figures can later be reconstructed
without recalibrating the curves.

## Historical sections

The sections currently present are:

- `01_synthetic_reference/` — experimental evidence for the frozen synthetic known-truth scenario.
- `02_bootstrap_recovery/` — mixed historical sequential-bootstrap and recovery evidence.
- `03_curve_validation/` — historical sequential-bootstrap assurance and independent repricing.
- `04_curve_diagnostics/` — historical log-linear curve-shape diagnostics.
- `05_quote_sensitivity/` — no persisted section currently available.
- `06_interpolation_comparison/` — historical interpolation-comparison evidence; persisted files reflect the available comparison outputs.
- `07_global_sensitivity/` — simultaneous-calibration sensitivity, propagation, and locality evidence.

The reports are based on synthetic inputs where documented and must not be
interpreted as observed-market data or as the operational baseline contract.