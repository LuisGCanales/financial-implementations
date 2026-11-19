# Python Integration — MXN F-TIIE OIS Curve

This guide explains how an external Python consumer obtains, checks, and queries the project's **selected MXN F-TIIE OIS term structure**. The standard baseline uses **simultaneous calibration with natural cubic interpolation of continuously compounded zero rates**.

It is an **in-memory financial interface**: the caller supplies OIS par quotations and a covered business calendar, and receives a calibrated curve together with calibration and acceptance diagnostics. File loading, execution provenance, and publishing artifacts belong to separate workflows.

## 1. Construct the selected baseline

Import the entry point explicitly:

```python
from yield_curves.baseline import build_baseline_ftiie_curve
```

Its Python signature is:

```python
def build_baseline_ftiie_curve(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    initial_discount_factors: Sequence[float] | None = None,
) -> BaselineResult:
    ...
```

| Argument | Financial meaning |
|---|---|
| `quotes` | Ordered F-TIIE OIS **par quotations**, including a common trade date, tenor labels, contractual maturities, and decimal fixed rates |
| `calendar` | The holiday/weekend calendar used to construct effective dates, 28-day schedules, overnight observations, and payment dates; **explicit coverage** is required |
| `initial_discount_factors` | Optional positive nodal discount factors to initialize simultaneous calibration; if omitted, a **log-linear sequential bootstrap** supplies the starting values |

The API selects the baseline's calibration method and interpolation representation; they are **not runtime switches** on this entry point. For other supported combinations, see [Interpolation](interpolation.md) and [Methodology](methodology.md).

No CSV, YAML, report file, or synthetic reference function is read implicitly. For loading files and preserving source declarations, see [Input contract](input_contract.md).

## 2. Complete in-memory example

The following illustration uses **invented quotations and a weekend-only teaching calendar**. It exercises the Python consumer path, **not an official MXMC holiday dataset or an observed-market calibration**.

Run from the `fixed-income/yield-curves` checkout with Python 3.11 and the project installed as described in the [README](../README.md#reproducibility).

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

result = build_baseline_ftiie_curve(
    quotes=quotes,
    calendar=calendar,
)

if not result.accepted_for_use:
    raise RuntimeError(result.acceptance.issues)

curve = result.curve
start_date = date(2026, 10, 1)
end_date = date(2026, 10, 29)

assert curve.reference_date <= start_date < end_date <= curve.node_dates[-1]

print("discount_factor =", curve.discount_factor(start_date))
print("zero_rate =", curve.zero_rate(start_date))
print("forward_rate_28d =", curve.forward_rate(start_date, end_date))
```

The curve reference date is the **common OIS effective date**, and the final supported pillar is the **last payment date**. Dates between them are evaluated using the selected interpolation. The zero rate is **continuously compounded**; the forward over the supplied interval is **simple ACT/360**. Rates are returned as decimals, not percentages.

The example neither creates a persisted execution nor publishes a curve. A complete synthetic demonstration that **does** produce a run archive is available separately in [`scripts/demo/`](../scripts/demo/README.md).

## 3. Understand the result and acceptance boundary

`BaselineResult` provides several distinct layers:

| Result field | What it means |
|---|---|
| `calibration_result` | Calibrated curve, numerical solver status/diagnostics, method, and per-quote calibration checks |
| `acceptance` | Standard assessment of structural validity, independently reconstructed OIS repricing, tolerances, and issue codes |
| `financial_context` | Captured financial inputs and selected methodology/policy, separate from file-source provenance |
| `curve` | Convenience property exposing the calibrated curve |
| `accepted_for_use` | Whether the result passed standard acceptance **and its currently held values remain consistent with the assessed payload** |

**Check `result.accepted_for_use` immediately before downstream use.** The stored `result.acceptance.accepted_for_use` alone describes the original assessment; it is not the same as the live value-binding check. The live check verifies bound values and policy; it does **not** rerun calibration or independent repricing.

Construction validates financial inputs and declared calendar coverage before solving; invalid inputs can raise `BaselineInputError` or `CalendarCoverageError`. Solver errors can also propagate. If a result is returned but not accepted, inspect `result.acceptance.issues` rather than treating numerical convergence as sufficient.

An accepted result is **not** proof of genuine market-data provenance, a correct future holiday calendar, unique true-curve recovery, or institutional production suitability.

[Acceptance and error contracts](validation.md) · [Scope and limitations](assumptions_limitations.md)

## 4. Consumer responsibilities and boundaries

Consumers should provide finance-appropriate quotes and calendar coverage, preserve the **single-curve projection/discounting assumption**, check acceptance, and request dates **only within the calibrated range**. Automatic extrapolation is unsupported.

The public curve object supports:

```python
curve.discount_factor(target_date)
curve.zero_rate(target_date)
curve.forward_rate(start_date, end_date)
```

For downstream valuation or risk processes, depend on the **financial curve interface and explicit input contracts**, not research scripts, reference-curve generators, saved experimental tables, or the order of experiment execution. Research reports help evaluate a method; they are **not** live curve inputs.

## 5. Persisted executions are a separate interface

When persistence and source provenance are needed, use the execution and snapshot workflow:

```python
from yield_curves.execution import build_baseline_execution
from yield_curves.snapshots import export_baseline_snapshot

execution = build_baseline_execution(
    dataset=dataset,
    calendar=calendar,
)

exported = export_baseline_snapshot(
    execution=execution,
    output_root=output_root,
)
```

Here `dataset` is an explicitly loaded `OISQuoteDataset`, and `output_root` is a caller-owned destination. Publication requires the workflow-issued execution envelope and standard acceptance; it is not achieved by attaching provenance to an arbitrary curve result.

The snapshot layout includes:

```text
<output_root>/
  current.json
  runs/<run-id>/
    input_quotes.csv
    calendar.json
    curve_nodes.csv
    quote_repricing.csv
    metadata.json
    manifest.json
```

Only an **accepted** execution can replace `current.json`; a complete rejected standard execution may still be archived without promotion. The pointer resolves an accepted run with the supported snapshot schema; it is not an interface for arbitrary-date curve pricing.

For command-line use and no-solve snapshot verification, see [CLI workflows](cli.md). For the complete persistence, integrity, and publication contract, see [Snapshots](snapshots.md).
