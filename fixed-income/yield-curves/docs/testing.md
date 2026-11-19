# Testing and Numerical Reproducibility

This guide describes how to run the project's **financial, numerical and software-contract tests**. Automated testing is distinct from the acceptance of an individual calibrated curve and from evidence of real-market pricing suitability.

The [test coverage map](test-coverage-map.md) links specific modules to their validation contracts, while the [research evidence index](evidence/index.md) documents controlled calibration and sensitivity experiments.

## Installation

The supported Python range is `>=3.11,<3.12` (Python 3.11 only).
Start at the `financial-implementations` Git repository root, then enter the
project directory before running installation or test commands:

```bash
cd fixed-income/yield-curves
```

From that project working directory:

```bash
python -m pip install -e .                # core: NumPy and SciPy
python -m pip install -e '.[dev]'         # pytest, tests without plotting
python -m pip install -e '.[dev,plots]'   # full collection, including plotting
```

For the reference Linux x86_64 platform, use Python 3.11.15 and the existing
hash-pinned dependencies, including the editable-install backend:

```bash
python -m pip install --require-hashes --only-binary=:all: \
  -r requirements/ci-reference.txt -r requirements/development-build.txt
python -m pip install --no-deps --no-build-isolation -e .
```

The lock targets glibc >=2.34 and includes Matplotlib for full collection.
Use a project-local `.venv` for reproducible local work; the pinned reference environment is described above. Keep editable metadata: snapshots and
external baseline consumers read the installed project version. These build
backend dependencies support local installation, not distribution certification.

`tests/tooling/test_reporting.py` imports matplotlib during collection, so even
whole-suite `-m 'not slow'` collection requires `plots`. With only `dev`, use
`pytest --ignore=tests/tooling/test_reporting.py -m 'not slow'` or select individual
non-plotting test files. PyYAML is not a runtime dependency.

## Choosing ordinary and expensive tests

```bash
pytest -q -m 'not slow'                 # normal development feedback
pytest --collect-only -q               # all tests, no execution
pytest --collect-only -q -m 'not slow'
pytest --collect-only -q -m slow
```

Plain `pytest` selects everything. Slow execution is an explicit, separate task:

```bash
pytest -s -vv -m slow --durations=20
```

`slow` describes expensive numerical work, independently of integration
semantics. It is not assigned merely for using simultaneous calibration or a
long dated curve. Every consumer of an expensive shared fixture is marked so
excluding slow tests avoids constructing that fixture.

Collection enumerates cases and applies marker selection; it does not execute
tests or establish passes. The [test coverage map](test-coverage-map.md) records
the audited revision, module/function/case counts, contracts and tolerances.
A non-slow selection is not a timing measurement or a code-coverage percentage.

## Computational cost and slow tests

The `slow` marker identifies **expensive repeated calibration and quote-sensitivity sweeps**, rather than every test that uses the simultaneous solver or a long-dated curve.

| Test category | Work performed | Selected by |
|---|---|---|
| Sequential one-sided quote shocks | One base curve and 15 recalibrations with forward diagnostics across 30 years | `slow` |
| Sequential central quote shocks | One base curve and 30 shocked recalibrations | `slow` |
| Simultaneous global sensitivity | One base curve and 30 recalibrations with dense forward grids | `slow` |
| Baseline regression and small method comparisons | Bounded builds, fixed numerical references and independent repricing | Non-slow |
| Conventions, pricing, validations, reporting and CLI tooling | Unit financial identities, structural rejections and small plotting helpers | Non-slow |

These classifications describe expected **computational structure**, not measured running times. The global sensitivity fixture reports progress when pytest output capture is disabled (`-s`); the financial library itself does not print by default.

## Numerical reference maintenance

See [scripts/tests/README.md](../scripts/tests/README.md) for explicit candidate
commands and the human review workflow. Neither candidate tool can update the
canonical fixture or frozen CSV. Reference generation is not part of ordinary
test execution. The baseline regression test retains its existing tolerances:

```bash
pytest -q tests/calibration/test_baseline.py
pytest -q tests/tooling/test_reference_candidates.py
```

A successful non-slow run does not claim slow coverage. Keep financial fixtures,
assertions, tolerances and numerical reference review independent of test counts.

## Continuous integration and manual numerical runs

The PR/main workflow installs the reference dependencies and complete checkout
editably, then runs `python -m pytest -q -m 'not slow'`. It does not build or
certify distributions. Scope detection runs without top-level path filters.
Changes under `fixed-income/yield-curves/` or `.github/workflows/` select validation;
irrelevant monorepo changes skip validation and still finish the aggregate check.

The exact required-check name is **`yield-curves-required`**. It always runs after
scope and validation: scope must succeed; relevant changes require successful
validation; irrelevant changes require skipped validation. Failed, cancelled or
unknown results fail closed. The configured required check is part of the existing repository rules; this documentation update does not change branch protection.

The manual `Yield curves numerical` workflow takes a full commit SHA, verifies
the checkout identity and runs `python -m pytest -s -vv -m slow --durations=20`
in one serial session. Select a revision containing the development setup above.
This is expensive financial verification; there are no release approval, version,
archive or package-consumer gates and no fixed test-count/selection-hash gate.

Both workflows set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
`MKL_NUM_THREADS=1` and `MPLBACKEND=Agg`. Temporary test, plotting and cache paths
live under the runner's temporary directory. Small result artifacts contain
JUnit, pytest output, checkout/subtree SHA and Python/dependency versions; they
do not upload generated datasets or snapshots. PR artifacts last 14 days and
manual numerical artifacts 30 days. A cancelled job may not finish its upload.

For comparable local runs, set the same thread/backend variables before starting
Python and use new temporary output/cache directories. Recorded counts in the coverage map describe a specified collected revision, not a permanent CI contract or a new test-execution claim.
