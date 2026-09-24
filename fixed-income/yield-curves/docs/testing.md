# Testing Guide

This document describes how to run the test suite for the F-TIIE yield-curve project, with special attention to expensive integration tests marked with `slow`.

## Why `slow` exists

Most tests in the project are intended to run quickly. They verify local properties such as quote perturbation logic, date-grid construction, curve invariants, numerical identities, validation rules, and lightweight helper functions.

Some tests execute a full calibration experiment. For example, global quote-sensitivity analysis may require one base calibration, one `+1 bp` calibration for each quote, one `-1 bp` calibration for each quote, and dense forward diagnostics after each shocked calibration.

Those tests are valuable, but they should not have to run every time a small implementation detail changes. Pytest's `slow` marker separates these expensive integration tests from the normal fast suite.

## Pytest configuration

Register the marker in `pyproject.toml`.

If `[tool.pytest.ini_options]` already exists, add `markers` to that existing section rather than creating a duplicate section.

```toml
[tool.pytest.ini_options]
markers = [
    "slow: expensive full integration tests",
]
```

A test can then be marked with:

```python
@pytest.mark.slow
def test_full_global_sensitivity(...):
    ...
```

If several tests reuse the same expensive module-scoped fixture, mark each test that depends on that fixture as `slow`. This ensures that excluding slow tests also avoids constructing the expensive fixture.

## Normal development workflow

For routine development, run only the fast suite:

```bash
pytest -m "not slow"
```

Use this as the default when changing helper functions, local curve logic, reporting utilities, validation rules, lightweight diagnostics, or unit tests.

## Run only the expensive tests

```bash
pytest -m slow
```

For expensive tests, it is usually more useful to see live progress and timing:

```bash
pytest -s -vv -m slow --durations=20
```

The options mean:

- `-s`: disable stdout capture so progress messages appear immediately;
- `-vv`: show individual test names in more detail;
- `-m slow`: select only tests marked `slow`;
- `--durations=20`: report the 20 slowest setup/call/teardown phases.

Equivalent explicit form for live output:

```bash
pytest --capture=no -vv -m slow --durations=20
```

## Run the complete suite

```bash
pytest
```

For a diagnostic full-suite run:

```bash
pytest -s -vv --durations=20
```

## Run one expensive test

When diagnosing a bottleneck, run the exact test by node ID instead of the complete suite.

Example:

```bash
pytest -s -vv   tests/validation/test_global_sensitivity.py::test_global_sensitivity_report_metadata   --durations=10
```

The first test using an expensive fixture may appear to be "stuck" while pytest is actually constructing the fixture during the setup phase.

## How progress logging works

The global-sensitivity integration fixture uses a progress callback. The financial library itself does not print by default. Instead, the test fixture passes a callback such as:

```python
started = perf_counter()

def progress(message: str) -> None:
    elapsed = perf_counter() - started

    print(
        f"[cubic_global_report +{elapsed:8.2f}s] "
        f"{message}",
        flush=True,
    )
```

The callback can report milestones such as:

```text
base calibration starting
base calibration finished
shock 1/15 [1M] +1bp calibration starting
shock 1/15 [1M] +1bp calibration finished
shock 1/15 [1M] -1bp calibration starting
dense forward diagnostics starting
shock 1/15 [1M] complete
```

These messages are visible in real time only when pytest output capture is disabled, normally with:

```bash
pytest -s ...
```

The purpose is diagnostic: it should make clear whether runtime is concentrated in the base calibration, shocked calibrations, a specific maturity shock, dense forward evaluation, or another stage.

## Recommended test classification

Use `slow` for tests that execute a materially expensive end-to-end numerical experiment, especially when they involve repeated calibration or long dense grids.

Do not mark a test `slow` merely because it belongs to a numerically oriented module.

Fast tests include quote perturbation, date-grid construction, input validation, dataclass invariants, simple analytical sensitivities, curve interpolation identities, and serialization/reporting helpers.

Slow integration tests include the full 15-quote global sensitivity experiment, +/- shock recalibration across all pillars, 30Y dense forward diagnostics, and similarly large synthetic recovery experiments.

Where possible, slow tests should share expensive results through fixtures such as:

```python
@pytest.fixture(scope="module")
def cubic_global_report(...):
    ...
```

This ensures that the expensive experiment is calculated once and reused by all tests in the module.

## Useful commands cheat sheet

Fast development suite:

```bash
pytest -m "not slow"
```

Slow integration suite with live progress:

```bash
pytest -s -vv -m slow --durations=20
```

Everything:

```bash
pytest -s -vv --durations=20
```

One global-sensitivity test:

```bash
pytest -s -vv   tests/validation/test_global_sensitivity.py::test_global_sensitivity_report_metadata   --durations=10
```

Show registered markers:

```bash
pytest --markers
```

Collect tests without executing them:

```bash
pytest --collect-only -q
```

## Practical rule

During implementation, use:

```bash
pytest -m "not slow"
```

Before considering a numerically important feature complete, also run:

```bash
pytest -s -vv -m slow --durations=20
```

Before a release, major merge, or milestone commit, run the complete suite.
