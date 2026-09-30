# General quote inputs and calendar coverage

Stage 3 provides input helpers separately from the baseline Python API. Stage 4
integrates operational input checks into construction and acceptance. The
operational and assurance rebuild scripts use the general dataset loader with
explicit classification, calendar CSV, coverage and source. Synthetic/projected
defaults live only in the demo. See [CLI workflows](cli.md) and
[snapshots.md](snapshots.md) for publication behavior.

## CSV contract

Required columns (order is arbitrary):

```csv
tenor,trade_date,contractual_maturity_date,par_rate
1M,2026-09-15,2026-10-18,0.08
3M,2026-09-15,2026-12-18,0.081
```

- Files use comma-separated UTF-8 text, with an optional UTF-8 BOM.
- Required values must be nonempty; dates use `YYYY-MM-DD`.
- Rates are finite decimal numbers: `0.08` means 8%; zero/negative rates are valid.
  Percentage strings such as `8%` are rejected. No automatic unit conversion occurs.
- Contractual maturity must follow trade date. Calendar-adjusted instrument
  validity remains the responsibility of instrument construction.
- Duplicate headers, missing columns, malformed quoting and mismatched row lengths
  are rejected. Data errors include the file and physical CSV line number.
- Input order is preserved; the reader does not sort or deduplicate quotes.
  Existing calibration checks still require increasing pillars and a common
  effective/reference date.
- Extra columns are permitted. If `quote_type` is present, every value must be
  `PAR_OIS_RATE`. Other instrument types require their own adapter.

To load only the calibration objects:

```python
from yield_curves.quote_io import read_ois_quotes_csv

quotes = read_ois_quotes_csv("my_quotes.csv")  # tuple[OISQuote, ...]
```

This also reads `data/synthetic/ftiie_ois_quotes_v1.csv`. The minimal reader
discards source-specific metadata, including `scenario_id` and `data_class`.
Experiments that need that information continue to use
`synthetic.read_synthetic_ois_quotes_csv`, which retains the original objects.

## Explicit dataset provenance

For operational input preparation, retain the dataset's identity:

```python
from yield_curves.quote_io import QuoteSource, load_ois_quote_dataset_csv

dataset = load_ois_quote_dataset_csv(
    "my_quotes.csv",
    classification=QuoteSource.UNKNOWN,
    source="User-supplied OIS quotes",
)
quotes = dataset.quotes
provenance = dataset.provenance
```

Classification is explicitly `SYNTHETIC_REFERENCE_DATA` (`QuoteSource.SYNTHETIC`),
`OBSERVED_MARKET_DATA` (`QuoteSource.OBSERVED`), or `UNKNOWN`. Moving a file does
not change its classification. OBSERVED is a caller declaration; the loader does
not independently authenticate a market-data feed. If a CSV `data_class` value
is present and nonempty, it must match the declared classification, including
when UNKNOWN is declared.

Provenance retains the source label, resolved file path and SHA-256 of the exact
bytes parsed. The path describes delivery; classification describes data nature.
Changing whitespace or line endings changes the fingerprint even when the parsed
quotes are equal. The loader does not infer source information from directories.

## Calendar contract

```python
from datetime import date
from yield_curves.calendars_io import build_mxmc_calendar_from_csv

calendar = build_mxmc_calendar_from_csv(
    "holidays.csv",
    coverage_start=date(2026, 1, 1),
    coverage_end=date(2026, 12, 31),
    source="Supplied holiday dataset for 2026",
)
```

The holiday CSV requires a `date` column. Coverage is caller-declared and inclusive;
both bounds must be provided together and ordered. It cannot be inferred from
the earliest and latest holidays: ordinary business days may lie before/after
them. A declared range is a completeness assertion by the caller, not proof that
the holiday data is authoritative or complete.

The CSV builder records PROVIDED provenance, the source label (the resolved path
when omitted) and a fingerprint of the parsed bytes. PROVIDED does not mean
verified. A projected calendar explicitly records PROJECTED provenance and its
requested full-year coverage:

```python
from yield_curves.research.calendars import build_projected_mxmc_calendar

demo_calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2057)
```

With declared bounds, date queries and adjustments raise `CalendarCoverageError`
outside coverage. This includes weekends, shifts across a boundary, offset zero
and unadjusted date requests. Payment lags can therefore exceed coverage even
when the contractual maturity is inside it.

For compatibility, `BusinessCalendar(...)` and holiday constructors may still
omit coverage. Such legacy calendars retain their prior date behavior. They
cannot pass `require_coverage` or the explicit operational preflight below.
The baseline now requires declared coverage automatically, including when assessing
an existing calibration. Shared non-baseline utilities retain legacy compatibility.

## Prepare inputs and build a curve

After loading the two files above:

```python
from yield_curves.inputs import validate_calendar_coverage
from yield_curves.baseline import build_baseline_ftiie_curve

validate_calendar_coverage(quotes=dataset.quotes, calendar=calendar)
result = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar)
if not result.accepted_for_use:
    raise RuntimeError(result.acceptance.issues)
curve = result.curve
```

The explicit coverage preflight in this example is optional when calling the
baseline: construction now performs quote and calendar checks automatically.
Call `inputs.prepare_baseline_inputs` to run the complete operational input check
without calibration, or `validate_calendar_coverage` for coverage alone.

Preflight reconstructs each OIS to visit actual required dates, including
adjustments, payment lags and overnight observations. Coverage errors identify
the quote tenor. Construction rejects invalid inputs before invoking the solver;
standalone assessment returns a rejected acceptance with issue codes. See
[validation.md](validation.md) for the error contract. Rates may be zero or
negative; at least two quotes and strictly increasing unique maturities/payment
pillars are required for the cubic baseline.

Coverage checks do not authenticate the holiday source. No coverage is inferred
from the filename, calendar name or sparse holiday dates.

## Verification

`tests/unit/test_general_inputs.py` covers the CSV schema and errors, equality
with synthetic calibration fields, explicit provenance, declared boundaries,
payment dates beyond maturity and general CSV-to-baseline integration. Existing
calendar/instrument tests and the stage 1 numerical reference remain applicable.
