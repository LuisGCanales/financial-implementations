# Integration Contract

This document defines the Python contract for downstream consumers such as the
future `valuation-price-validation` flagship.

## Python API

```python
from yield_curves.baseline import build_baseline_ftiie_curve
```

The real signature is:

```python
def build_baseline_ftiie_curve(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    initial_discount_factors: Sequence[float] | None = None,
) -> BaselineResult:
    ...
```

The caller supplies quotes and a business calendar explicitly. An optional
initial discount-factor vector can be supplied for a nearby calibration; the
API otherwise obtains its own coherent initial guess.

The API does not read CSV, YAML, reports, or research scripts.

## Return object

`BaselineResult` contains:

- `calibration_result`: the underlying `GlobalCalibrationResult`, including the calibrated curve, solver diagnostics, calibration checks, method, and aggregate repricing diagnostics;
- `acceptance`: the operational acceptance result and independent repricing checks;
- `financial_context`: captured prepared financial inputs and the selected
  construction policy, distinct from file/source provenance;
- `curve`: a convenience property returning `calibration_result.curve`;
- `accepted_for_use`: historical acceptance **and** a current value-binding check
  against the calibration result and financial context.

Consumers should inspect `result.accepted_for_use` before downstream valuation.
The live check includes curve nodes, mutable cubic spline state, solver declarations
and acceptance policy; it does not recalibrate or reprice. The historical boolean
`result.acceptance.accepted_for_use` alone does not establish that current values
remain bound. An isolated assessment, including custom analytical tolerances,
does not establish standard publication authority. See [architecture](architecture.md)
and [snapshot authority](snapshots.md#execution-identity-and-publication-authority).

The curve object provides:

```python
curve.discount_factor(target_date)
curve.zero_rate(target_date)
curve.forward_rate(start_date, end_date)
```

The curve does not support extrapolation beyond its calibrated node range.

## Complete synthetic in-memory example

Run from `fixed-income/yield-curves` with the package available in Python 3.11.
This educational example uses two invented OIS quotes and an explicitly covered,
weekend-only calendar. It makes no real-market holiday or MXMC data claim and
requires neither research imports nor filesystem adapters. The supplied dates
are contractual maturities; instrument construction derives payment pillars.

```python
from datetime import date
from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.calendars import BusinessCalendar
from yield_curves.quotes import OISQuote

quotes = (
    OISQuote("1M", date(2026, 9, 15), date(2026, 10, 19), 0.05),
    OISQuote("3M", date(2026, 9, 15), date(2026, 12, 17), 0.051),
)
calendar = BusinessCalendar(
    "WEEKENDS_ONLY_TEACHING_EXAMPLE",
    holidays=frozenset(),
    weekend_days=frozenset({5, 6}),
    coverage_start=date(2026, 1, 1),
    coverage_end=date(2026, 12, 31),
)
result = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)
print(f"accepted_for_use = {str(result.accepted_for_use).lower()}")
if not result.accepted_for_use:
    raise RuntimeError(result.acceptance.issues)
curve = result.curve
query_date = date(2026, 10, 1)
forward_end = date(2026, 10, 29)
assert curve.reference_date <= query_date < forward_end <= curve.node_dates[-1]
print("discount_factor =", curve.discount_factor(query_date))
print("zero_rate =", curve.zero_rate(query_date))
print("forward_rate_28d =", curve.forward_rate(query_date, forward_end))
```

Zero and forward rates are decimal rates; the forward is over 28 calendar days.
All queries stay between the effective reference date and final payment pillar.
This example exercises the public consumer path without issuing an execution
envelope or publishing a snapshot. The checkout demo is
[`scripts/demo/build_synthetic_baseline.py`](../scripts/demo/build_synthetic_baseline.py);
there is no validated Jupyter notebook in this subproject.

## Consumer responsibilities

Consumers must:

- provide correctly classified and ordered quotes;
- provide a calendar appropriate for those instruments;
- check `accepted_for_use`;
- respect the curve reference date and calibrated coverage;
- handle rejected results explicitly;
- keep projection and discounting assumptions visible in downstream workflows.

## What consumers should not depend on

The flagship must not depend on:

- `scripts/experiments/`;
- historical `outputs/research/`;
- synthetic known-truth functions;
- research metadata;
- the execution order of experiment scripts.

## Snapshot artifacts

`scripts/operational/build_baseline_curve.py` requires the caller's explicit
`--output-root`. For a caller-owned destination:

```bash
OUTPUT_ROOT="$(mktemp -d)"
# Supply the other required quote/calendar flags described in cli.md:
# python scripts/operational/build_baseline_curve.py ... --output-root "$OUTPUT_ROOT"
```

Its layout is relative to that destination:

```text
<output_root>/current.json
<output_root>/runs/<run-id>/
```

Resolve `current.json` to the run before reading its payloads; see
[snapshot layout](snapshots.md). The former flat schema-1.0 files are historical
artifacts under `outputs/baseline/legacy/schema-1.0/`, with no current fallback.

Run files provide an auditable operational snapshot and provenance. They are
not the primary curve interface and do not replace the Python curve object for
arbitrary-date interpolation or forward calculations.
