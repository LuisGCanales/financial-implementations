# Yield-Curve Bootstrapping & Validation

This project implements transparent MXN F-TIIE OIS curve construction, pricing, validation, diagnostics, and sensitivity analysis.

It separates reusable financial code from the current operational baseline, baseline assurance, and historical research workflows.

## What this project demonstrates

- Explicit F-TIIE OIS financial conventions and MXMC calendar handling.
- OIS schedules, overnight observations, instruments, and pricing.
- Sequential bootstrap and simultaneous nodal calibration.
- Independent repricing and structural acceptance checks.
- Curve-shape diagnostics and quote-sensitivity research.
- A reusable Python API for the current project-selected baseline.

## Current baseline

The current operational baseline is:

```text
simultaneous nodal calibration
        +
CUBIC_CONTINUOUS_ZERO
```

Nodal discount factors are solved together and continuous zero rates are represented with a natural cubic spline. This is the selected baseline for the current implementation, not a claim of universal superiority.

The rationale and trade-offs are documented in [docs/methodology.md](docs/methodology.md) and [docs/assumptions_limitations.md](docs/assumptions_limitations.md).

## Architecture

```text
reusable financial library
        ↓
yield_curves.baseline
        ↓
operational workflow
        ↓
outputs/baseline/
        ↓
external consumer / flagship
```

In parallel:

```text
baseline result → assurance workflow → acceptance evidence

historical development workflows → scripts/experiments/ → reports/
```

The flagship must depend on the Python baseline API, not on research scripts or historical reports.

## Quick start

Python 3.11 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Runtime dependencies are NumPy, SciPy, and PyYAML. Plotting dependencies are optional:

```bash
python -m pip install -e ".[dev,plots]"
```

Build the current demonstration baseline from the frozen synthetic quote set:

```bash
python scripts/operational/build_baseline_curve.py
```

Validate the current baseline:

```bash
python scripts/assurance/validate_baseline_curve.py
```

The operational snapshot is written to `outputs/baseline/`.

## Python API

```python
from yield_curves.baseline import build_baseline_ftiie_curve

result = build_baseline_ftiie_curve(
    quotes=quotes,
    calendar=calendar,
)

if result.accepted_for_use:
    curve = result.curve
```

The API does not read CSV, YAML, reports, or research outputs. See [docs/integration_contract.md](docs/integration_contract.md).

## Repository structure

```text
yield-curves/
├── config/                 # descriptive project specifications
├── data/                   # calendars and frozen synthetic inputs
├── docs/                   # conventions, methodology, contracts, limits
├── outputs/baseline/       # current operational snapshot
├── reports/                # historical analytical and research evidence
├── scripts/
│   ├── operational/        # current baseline workflow
│   ├── assurance/          # current baseline acceptance workflow
│   └── experiments/        # historical and research workflows
├── src/yield_curves/       # reusable financial library and baseline API
├── tests/
├── CHANGELOG.md
└── pyproject.toml
```

## Operational outputs

`outputs/baseline/` contains the current snapshot, not the primary curve API:

- `curve_nodes.csv`: tenor, pillar date, discount factor, and continuous zero rate.
- `quote_repricing.csv`: input quote, independently repriced quote, error, and status.
- `metadata.json`: baseline identity, provenance, method, solver state, acceptance, and tolerances.

For arbitrary-date discount factors, zero rates, and forwards, consumers must use the Python curve object rather than reconstructing a dense curve from CSV.

## Analytical evidence

`reports/` contains historical analytical, diagnostic, and experimental evidence generated during development. It is not the operational delivery mechanism.

- `01_synthetic_reference`: synthetic known-truth reference evidence.
- `02_bootstrap_recovery`: historical bootstrap and recovery evidence.
- `03_curve_validation`: historical sequential-bootstrap validation.
- `04_curve_diagnostics`: historical log-linear diagnostics.
- `05_quote_sensitivity`: no persisted section currently available.
- `06_interpolation_comparison`: historical interpolation comparison evidence.
- `07_global_sensitivity`: simultaneous-calibration propagation and locality evidence.

Reports use synthetic data where documented and must not be interpreted as observed market data.

## Testing

Fast unit and calibration tests:

```bash
pytest -m "not slow"
```

The global sensitivity integration tests are marked `slow`. Some historical quote-sensitivity fixtures still perform repeated recalibration without the `slow` marker; run those tests selectively when needed. See [docs/testing.md](docs/testing.md).

## Scope and limitations

- The canonical instrument is MXN F-TIIE OIS.
- Core v1 uses one curve for projection and discounting as a project assumption.
- The operational input demonstration is synthetic, not observed market data.
- The current API does not claim CME or bank production-curve replication.
- Extrapolation beyond calibrated coverage is not supported.
- The projected calendar has explicit coverage limitations.
- Cubic interpolation is globally coupled and has documented sensitivity/locality trade-offs.
- Synthetic known-truth recovery does not establish real-market robustness.
- A multi-curve discounting architecture is outside the current scope.
- PCHIP is implemented as an experimental extension and is not the selected baseline.

Perfect instrument calibration is not the same as true-curve recovery. A calibration can reprice its inputs while still depending materially on the interpolation and assumptions between nodes.

## Status

The yield-curve implementation is functionally closed for feeding the future `valuation-price-validation` flagship through the baseline API and operational snapshot. Historical methodology research remains available for maintenance and future, separately scoped investigation.
