# OIS Quote Inputs and Calendar Coverage

This guide describes how **F-TIIE OIS par quotations and business-day calendars** are supplied, classified, and checked before constructing a yield curve. Market data and calendars are **caller-provided** in the standard workflow; the frozen synthetic dataset and projected calendar are selected only by the separate demonstration.

The [integration contract](integration_contract.md) describes the in-memory curve API, while [CLI workflows](cli.md) covers command-line execution and snapshot publication.

## 1. Financial inputs

Each calibration quotation identifies a par-rate OIS through four required fields:

| Field | Meaning | Example |
|---|---|---|
| `tenor` | Quote label, retained for identification | `1M` |
| `trade_date` | Common trade date in ISO format | `2026-09-15` |
| `contractual_maturity_date` | Unadjusted maturity supplied for the instrument | `2026-10-18` |
| `par_rate` | Annual rate in **decimal units** | `0.08` = 8% |

These fields supply the contract; they are **not** the resulting adjusted schedule or curve pillar dates. Instrument construction applies the relevant [F-TIIE OIS conventions](conventions.md), derives the common effective/reference date, adjusts the schedule, and determines each instrument's final **payment-date** calibration pillar.

### CSV format

The general CSV reader requires these four columns, in any order:

```csv
tenor,trade_date,contractual_maturity_date,par_rate
1M,2026-09-15,2026-10-18,0.08
3M,2026-09-15,2026-12-18,0.081
```

- UTF-8, optionally with a BOM; dates must use `YYYY-MM-DD`.
- Rates must be finite decimal numbers. **Zero and negative rates are permitted**; values such as `8%` are not parsed or automatically converted.
- Required fields must be nonempty; contractual maturity must follow trade date.
- Additional columns are accepted. If `quote_type` is present, it must be `PAR_OIS_RATE`.
- Rows retain their input order. The loader does **not** sort, deduplicate, or convert tenor labels into maturity dates.
- Duplicate headers, malformed rows, invalid rates, and unsupported quote types produce explicit errors, with line information where applicable.

For a set intended for the selected cubic baseline, supply at least **two** quotes with distinct tenor labels, one trade date, strictly increasing contractual maturities, and ultimately strictly increasing payment pillars.

To obtain only quote objects:

```python
from yield_curves.quote_io import read_ois_quotes_csv

quotes = read_ois_quotes_csv("my_quotes.csv")
```

This minimal reader does not preserve file-source metadata. The quote objects provide the financial fields consumed by calibration and repricing.

## 2. Dataset classification and provenance

For workflows where the origin and classification of inputs must be retained, use the dataset loader:

```python
from yield_curves.quote_io import QuoteSource, load_ois_quote_dataset_csv

dataset = load_ois_quote_dataset_csv(
    "my_quotes.csv",
    classification=QuoteSource.UNKNOWN,
    source="User-supplied F-TIIE OIS quotations",
)

quotes = dataset.quotes
provenance = dataset.provenance
```

The three declarations are:

| Classification | Code value | Interpretation |
|---|---|---|
| Synthetic reference data | `QuoteSource.SYNTHETIC` | `SYNTHETIC_REFERENCE_DATA` |
| Observed market data | `QuoteSource.OBSERVED` | `OBSERVED_MARKET_DATA` |
| Unknown origin | `QuoteSource.UNKNOWN` | `UNKNOWN` |

Classification is **explicit**, never inferred from a filename, path, or quote level. If the CSV contains a nonempty `data_class`, it must agree with the caller's declared classification. In particular, **`OBSERVED_MARKET_DATA` is a caller assertion, not external authentication** of a market feed.

Provenance records the declared source label, resolved file path, and SHA-256 of the **exact input bytes**. The hash checks file identity, not financial truth; even a whitespace change can produce a different hash without changing the parsed quotations.

The [synthetic research dataset](../data/synthetic/README.md) includes extra columns such as its scenario identifier and derived dates. The general reader retains only the common financial quote fields; the research-specific reader can retain the additional scenario information.

## 3. Calendar inputs and coverage

The OIS contracts require Mexico City (MXMC) business-day logic for effective dates, adjusted coupon boundaries, overnight fixing periods, and payment lags.

A supplied calendar CSV requires a `date` column of ISO holiday dates. Optional descriptive columns are ignored by the calendar loader.

```csv
date
2026-01-01
2026-02-02
2026-09-16
```

Build a calendar with **explicit inclusive coverage**:

```python
from datetime import date
from yield_curves.calendar_io import build_mxmc_calendar_from_csv

calendar = build_mxmc_calendar_from_csv(
    "holidays.csv",
    coverage_start=date(2026, 1, 1),
    coverage_end=date(2026, 12, 31),
    source="Supplied holiday file for 2026",
)
```

Coverage is declared by the caller, **not inferred from the first or last holiday**. A declaration does not prove the holiday list is complete or officially sourced. The resulting calendar retains `PROVIDED` provenance and a fingerprint of the bytes used to construct it; `PROVIDED` is not a verification status.

Coverage must include **every date required to construct and value the instruments**, not just their contractual maturities. Business-day adjustments and the two-business-day payment lag can extend beyond the last contractual date. Out-of-range date operations raise `CalendarCoverageError`.

For controlled research only, a separately labeled projected calendar is available:

```python
from yield_curves.research.calendars import build_projected_mxmc_calendar

research_calendar = build_projected_mxmc_calendar(
    start_year=2026,
    end_year=2057,
)
```

This generates reproducible **projected**, not official, future holidays. See [calendar sources and limitations](../data/calendars/README.md).

A `BusinessCalendar` may be constructed without declared coverage for some lower-level utilities, but such a calendar **cannot pass the standard baseline's coverage requirements**.

## 4. Prepare and calibrate

After loading `dataset` and `calendar`:

```python
from yield_curves.baseline import build_baseline_ftiie_curve

result = build_baseline_ftiie_curve(
    quotes=dataset.quotes,
    calendar=calendar,
)

if not result.accepted_for_use:
    raise RuntimeError(result.acceptance.issues)

curve = result.curve
```

The selected baseline **automatically validates the financial input set and calendar coverage before calibration**. When a separate preflight is useful:

```python
from yield_curves.inputs import (
    prepare_baseline_inputs,
    validate_calendar_coverage,
)

prepared = prepare_baseline_inputs(
    quotes=dataset.quotes,
    calendar=calendar,
)
# Or check calendar coverage alone:
validate_calendar_coverage(
    quotes=dataset.quotes,
    calendar=calendar,
)
```

Input preparation validates the shared trade date, maturity and pillar ordering, distinct tenors, finite rates, required covered dates, and reconstructable OIS instruments. It removes **outer whitespace** from tenor labels when capturing financial identity—so `" 1M "` and `"1M"` are duplicates—but does not change their case, rewrite internal whitespace, or infer tenor aliases. Caller quote objects are not mutated.

Invalid baseline quote sets raise `BaselineInputError` with issue codes; insufficient calendar coverage raises `CalendarCoverageError`. The baseline does not silently replace missing inputs with synthetic quotes or a projected calendar. Rejected numerical results must not be treated as accepted merely because an optimizer terminated successfully.

Input validation confirms consistency with the *supplied* values. It does not certify data authenticity, market-calendar correctness, or financial suitability.

## Related documentation

- [Financial conventions](conventions.md) — how dates, coupons, fixings and payment dates are defined.
- [Input and acceptance validation](validation.md) — issue codes and rejection conditions.
- [Python integration contract](integration_contract.md) — curve results and downstream usage.
- [CLI workflows](cli.md) — file-based calibration, assurance and synthetic demonstrations.
- [Research-data provenance](../data/synthetic/README.md) — known-truth generation and experimental classification.
