# Testing Guide

## Installation

Python 3.11 or later is required. From the repository root:

```bash
python -m pip install -e .                # core: NumPy and SciPy
python -m pip install -e '.[dev]'         # pytest, tests without plotting
python -m pip install -e '.[dev,plots]'   # full collection, including plotting
```

`tests/tooling/test_reporting.py` imports matplotlib during collection, so even
whole-suite `-m 'not slow'` collection requires `plots`. With only `dev`, use
`pytest --ignore=tests/tooling/test_reporting.py -m 'not slow'` or select individual
non-plotting test files. PyYAML is not a runtime dependency.

## Selection

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

## Structural cost audit

| Test/group | Work performed | Marker before | Marker now | Reason |
|---|---|---|---|---|
| Quote sensitivity: `report`, 10 tests | Load 15 frozen quotes; 1 base + 15 sequential shock calibrations; weekly forward grids across 30Y; no plots | none | slow | Repeated full-curve recalibration |
| Quote sensitivity: `central_report`, 7 tests | Load 15 quotes; 1 base + 30 sequential shock calibrations; weekly forwards; no plots | none | slow | Two-sided full-curve sweep |
| Global sensitivity: `cubic_global_report`, 10 tests | Load 15 quotes; 1 base + 30 simultaneous calibrations; dense forward diagnostics; no plots | slow | slow | Expensive numerical experiment |
| Small sensitivity contracts | Two short quotes, 3–5 small calibrations, or analytical helpers; no plots | none | none | Bounded work suitable for normal feedback |
| Baseline regression | One shared 15-quote baseline build; frozen JSON comparison and repricing; no plots | none | none | Essential regression without a shock sweep |
| Simultaneous/interpolation/bootstrap tests | Individual builds and method comparisons; short warm-start contract cases; some CSV loading; no plots | none | none | Direct engine coverage, no research-scale sweep |
| Recovery/horizon/diagnostics/validation | Analytical curves or single sequential builds, grids and repricing; no shock recalibration loop or plots | none | none | Grid horizon alone does not justify slow |
| Reporting/presentation helpers | Temporary plots or extracted date helpers; no calibration | none | none | Lightweight rendering/helper contracts |
| Reference tooling | Output guards, small public baseline builds, serialization; no full reference generation | none | none | Safety coverage without a full experiment |

This is a structural classification, not a timing benchmark. The global fixture
prints progress through its callback with `-s`; the financial library itself does
not print by default.

## Numerical reference maintenance

See [scripts/tests/README.md](../scripts/tests/README.md) for explicit candidate
commands and the human review workflow. Neither candidate tool can update the
canonical fixture or frozen CSV. Reference generation is not part of ordinary
test execution. The baseline regression test retains its existing tolerances:

```bash
pytest -q tests/calibration/test_baseline.py
pytest -q tests/tooling/test_reference_candidates.py
```

Full suite and separately scheduled slow verification belong to release or
numerical-change review; a successful fast run does not claim slow coverage.
