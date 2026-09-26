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
) -> BaselineResult
```

The caller supplies quotes and a business calendar explicitly. An optional
initial discount-factor vector can be supplied for a nearby calibration; the
API otherwise obtains its own coherent initial guess.

The API does not read CSV, YAML, reports, or research scripts.

## Return object

`BaselineResult` contains:

- `calibration_result`: the underlying `GlobalCalibrationResult`, including the calibrated curve, solver diagnostics, calibration checks, method, and aggregate repricing diagnostics;
- `acceptance`: the operational acceptance result and independent repricing checks;
- `curve`: a convenience property returning `calibration_result.curve`;
- `accepted_for_use`: a convenience property for `acceptance.accepted_for_use`.

Consumers should inspect `accepted_for_use` before downstream valuation.

The curve object provides:

```python
curve.discount_factor(target_date)
curve.zero_rate(target_date)
curve.forward_rate(start_date, end_date)
```

The curve does not support extrapolation beyond its calibrated node range.

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
- historical `reports/`;
- synthetic known-truth functions;
- research metadata;
- the execution order of experiment scripts.

## Snapshot artifacts

`scripts/operational/build_baseline_curve.py` writes:

```text
outputs/baseline/curve_nodes.csv
outputs/baseline/quote_repricing.csv
outputs/baseline/metadata.json
```

These files provide an auditable operational snapshot and provenance. They are
not the primary curve interface and do not replace the Python curve object for
arbitrary-date interpolation or forward calculations.
