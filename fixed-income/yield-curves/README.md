# MXN F-TIIE OIS curves: construction and validation

This financial research and engineering implementation studies how instrument
conventions, calibration and interpolation affect MXN F-TIIE OIS curves,
repricing and sensitivities. Frozen synthetic inputs support controlled
known-truth experiments and reproducible numerical comparisons.

Core-v1 uses MXMC calendars, T+2 effective dates, ACT/360, 28-day coupon periods,
overnight compounding and a two-business-day payment lag. Projection and
discounting share one curve as an explicit project assumption. See
[conventions](docs/conventions.md) for the exact rules and calendar coverage.

Development prioritizes financial methodology, pricing and risk, numerical
robustness, reproducible scripts and useful scientific evidence. Python-package
distribution and release certification are retired; editable checkout installation
and package metadata remain for the Python API, snapshots and flagship consumers.

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

Sequential bootstrap, log-linear discount factors and linear-zero interpolation
support methodological comparisons; PCHIP remains experimental. Independent
repricing and acceptance checks accompany calibration.

The rationale and trade-offs are documented in [docs/methodology.md](docs/methodology.md) and [docs/assumptions_limitations.md](docs/assumptions_limitations.md).

## Architecture

Developer navigation: [technical architecture](docs/architecture.md),
[extension roadmaps](docs/extending.md), and [test coverage map](docs/test-coverage-map.md).

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

Use Python 3.11 (`>=3.11,<3.12`). Start at the `financial-implementations`
repository root. Reuse the project `.venv` when it exists; create it only for a
fresh checkout:

```bash
cd fixed-income/yield-curves
# Fresh checkout only: python3.11 -m venv .venv
source .venv/bin/activate
```

For the Linux x86_64 reference platform (CPython 3.11.15, glibc >=2.34), install
hash-pinned financial, test, plot and editable-build dependencies:

```bash
python -m pip install --require-hashes --only-binary=:all: \
  -r requirements/ci-reference.txt -r requirements/development-build.txt
python -m pip install --no-deps --no-build-isolation -e .

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

The reference lock is platform-specific; do not reuse it on another platform.
For development elsewhere, `python -m pip install -e '.[dev,plots]'` resolves the
supported broad requirements without promising identical numerical results.
Repository scripts, fixtures and demo inputs require the complete checkout.
Editable installation also supplies version metadata used by snapshots and
`valuation-price-validation`. See [testing](docs/testing.md) for setup and CI.

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

See the [curated evidence index](docs/evidence/index.md), [unified claims](docs/evidence/claims.md) and [verified saved-data reproduction contract](docs/evidence/reproduce.md).

`outputs/research/` contains historical analytical, diagnostic, and experimental evidence generated during development. It is not the operational delivery mechanism.

- `01_synthetic_reference`: synthetic known-truth reference evidence.
- `02_bootstrap_recovery`: historical bootstrap and recovery evidence.
- `03_curve_validation`: historical sequential-bootstrap validation.
- `04_curve_diagnostics`: historical log-linear diagnostics.
- `05_quote_sensitivity`: historical output section absent; curated C04 sensitivity exhibits are available through the evidence index above.
- `06_interpolation_comparison`: historical interpolation comparison evidence.
- `07_global_sensitivity`: simultaneous-calibration propagation and locality evidence.

Reports use synthetic data where documented and must not be interpreted as observed market data.

## Testing

Fast unit and calibration tests:

```bash
python -m pytest -q -m "not slow"
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

## Future financial work

Priorities include observed-market inputs and maturity conventions, certified
calendar coverage, interpolation stability and locality, calibration robustness,
and a separately specified multi-curve architecture. New claims require new
financial evidence; see [extension roadmaps](docs/extending.md).
The existing baseline API and operational snapshots remain the integration
boundary for `valuation-price-validation`.

## License

The `fixed-income/yield-curves` subproject is licensed under the
[MIT License](LICENSE), copyright (c) 2026 Luis Gerardo Canales Ocampo.
This license applies only to this subproject, not to the rest of the monorepo.
