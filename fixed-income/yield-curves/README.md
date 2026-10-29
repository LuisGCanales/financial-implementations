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
explicit output_root (for example, outputs/baseline/)
        ↓
external consumer / flagship
```

In parallel:

```text
baseline result → assurance workflow → acceptance evidence

historical development workflows → scripts/experiments/ → outputs/research/
```

The flagship must depend on the Python baseline API, not on research scripts or historical reports.

## Quick start

The package supports Python 3.11 only (`>=3.11,<3.12`).
Run from a checkout of `financial-implementations`, starting at its repository
root, with no existing `.venv` in the project directory:

```bash
cd fixed-income/yield-curves
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

DEMO_ROOT="$(mktemp -d)"
python scripts/demo/build_synthetic_baseline.py \
  --output-root "$DEMO_ROOT"

python scripts/assurance/validate_baseline_curve.py \
  snapshot --output-root "$DEMO_ROOT"
```

This demo uses frozen **synthetic quotes** and a **projected 2026–2057 calendar**,
not observed market inputs. Both commands use the same explicit temporary
`output_root`; generated archives stay outside the checkout's tracked outputs.
Snapshot assurance verifies the published archive without recalibration or writes.
The operational CLI requires explicit inputs and an explicit output destination;
it does not select demo defaults. See [CLI workflows](docs/cli.md).

### Installation modes

- **Checkout development and repository scripts:** the editable installation above
  supplies the library while scripts, fixtures and frozen demonstration datasets
  come from the checkout. Runtime dependencies are NumPy and SciPy.
- **Wheel/sdist installation:** `python -m pip install /path/to/yield_curves-0.1.0-py3-none-any.whl`
  or `python -m pip install /path/to/yield_curves-0.1.0.tar.gz` installs the Python
  library. These distributions do not supply the repository scripts, test fixtures
  or frozen demonstration datasets needed for this Quickstart. There is no
  installed CLI command; script workflows require a checkout.
- **Optional tests and plots in a checkout:** `dev` adds pytest and `plots` adds
  Matplotlib. Full test collection, including plotting tests, requires both:

```bash
python -m pip install -e ".[dev,plots]"
```

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
├── outputs/baseline/       # example operational destination; legacy archive
├── outputs/research/       # historical analytical and research evidence
├── scripts/
│   ├── operational/        # current baseline workflow
│   ├── assurance/          # current baseline acceptance workflow
│   ├── demo/               # synthetic quotes and projected calendar
│   └── experiments/        # historical and research workflows
├── src/yield_curves/       # reusable financial library and baseline API
├── tests/
├── CHANGELOG.md
└── pyproject.toml
```

## Operational outputs

At the caller's explicit `output_root`, `current.json` resolves the current run
under `runs/<run-id>/`. For example, `--output-root outputs/baseline` uses
`outputs/baseline/current.json`; this is not an operational default.
The run contains these payloads among others (see [snapshots](docs/snapshots.md)):

- `curve_nodes.csv`: tenor, pillar date, discount factor, and continuous zero rate.
- `quote_repricing.csv`: input quote, independently repriced quote, error, and status.
- `metadata.json`: baseline identity, provenance, method, solver state, acceptance, and tolerances.

For arbitrary-date discount factors, zero rates, and forwards, consumers must use the Python curve object rather than reconstructing a dense curve from CSV.

Historical schema-1.0 flat files are archived under
`outputs/baseline/legacy/schema-1.0/`, preserving their original bytes and metadata.
They are never used as a current fallback.

## Analytical evidence

`outputs/research/` contains historical analytical, diagnostic, and experimental evidence generated during development. It is not the operational delivery mechanism.

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

Install `.[dev,plots]` before collecting the whole suite. Full quote-sensitivity
and global-sensitivity recalibration experiments are marked `slow`; individual
calibration and small contract tests remain in normal feedback. Plain `pytest`
runs all tests. See [docs/testing.md](docs/testing.md) for selection and safe
reference-candidate tooling.

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

## License

The `fixed-income/yield-curves` subproject is licensed under the
[MIT License](LICENSE), copyright (c) 2026 Luis Gerardo Canales Ocampo.
This license applies only to this subproject, not to the rest of the monorepo.
