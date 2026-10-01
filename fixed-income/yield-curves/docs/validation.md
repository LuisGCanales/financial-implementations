# Validation and Acceptance

The project distinguishes historical bootstrap validation from acceptance of
the current operational baseline.

## Historical bootstrap validation

The historical validation workflow operates on `BootstrapResult`. It checks
quote integrity, sequential solver steps, curve structure, discount-factor
validity, and independently reprices the calibration instruments. Its outputs
are preserved under `outputs/research/{tables,text}/03_curve_validation/` as historical evidence.

Those reports document the sequential/log-linear path. They are not the
acceptance contract for the current cubic baseline.

## Current operational baseline acceptance

`yield_curves.baseline` calibrates with simultaneous nodal calibration and
`CUBIC_CONTINUOUS_ZERO`. It first validates the quote set and declared calendar
coverage, then performs a baseline-specific acceptance check.

The acceptance checks:

- at least two quotes with nonempty unique tenors;
- valid dates, finite numeric rates, a common trade date and increasing unique maturities;
- declared calendar coverage for every required instrument date, including payment lags;
- a common effective date and strictly increasing payment pillars;
- solver/calibration success;
- expected interpolation method and an actual cubic continuous-zero curve;
- curve availability;
- node count equal to quote count;
- calibration check count and tenor ordering matching the quote set;
- curve reference date and node dates matching the reconstructed instruments;
- strictly increasing node dates;
- finite, strictly positive discount factors;
- independent reconstruction of each OIS from the input quote;
- independent recalculation of each model par rate;
- finite repricing errors;
- every independent repricing error within the PASS tolerance of `0.01 bp`.

Discount factors are not required to be strictly decreasing. That condition is
not universally valid across rate regimes.

The result exposes two different states:

```text
calibration_success
    solver found a numerical solution

accepted_for_use
    the solution also passed the operational checks above
```

Therefore:

```text
calibration_success != accepted_for_use
```

A result can converge and still be rejected for downstream use.

## What acceptance does not prove

Operational acceptance does not prove that quotes are observed-market correct,
that the curve is universally optimal, or that it matches a latent true curve.
Recovery against synthetic known truth is research evidence, not an
operational acceptance criterion.

## Shared repricing calculation

Both workflows delegate instrument reconstruction and par-rate calculation to
`yield_curves.repricing.reprice_calibration_instruments`, which accepts a curve,
quotes, calendar and tolerances. It does not consume solver residuals.

`validation.independently_reprice_calibration_instruments` adapts a sequential
result. `baseline._independently_reprice` adapts a simultaneous result and retains
baseline-specific non-finite issue codes. Shared PASS/REVIEW/FAIL classification
does not merge the workflows' curve-level policies.

## Build errors versus assessment rejection

`build_baseline_ftiie_curve` calls `inputs.prepare_baseline_inputs` before the
solver. Invalid quote sets raise `BaselineInputError`, a ValueError subclass with
an `.issues` tuple. Missing or insufficient calendar coverage raises
`CalendarCoverageError`. No fabricated calibration result is returned when
calibration has not run. Solver exceptions continue to propagate; a solver result
with `success=False` is rejected by acceptance.

`assess_baseline_calibration` also validates inputs when called independently.
It returns `accepted_for_use=False` and issue codes for invalid quote sets,
missing/insufficient coverage or incompatible curve structure. It skips repricing
when input/structural checks fail. `structural_valid` now includes the ability to
validate the curve's geometry against valid, covered input instruments.

The build path reuses prepared geometry for assessment. Pricing still rebuilds
the OIS independently, and both solvers keep their existing instrument preparation.
A standalone assessment performs its own preflight so it cannot bypass input
requirements. Legacy calendars without coverage remain usable by shared pricing
and calibration utilities, but cannot build or pass acceptance of the baseline.

Representative issue codes:

| Condition | Code |
|---|---|
| Empty / fewer than two quotes | `EMPTY_QUOTE_SET` / `INSUFFICIENT_QUOTES_FOR_CUBIC` |
| Invalid label, date or numeric rate | `INVALID_TENOR:<label>`, `INVALID_QUOTE_DATE:<label>`, `NON_FINITE_OR_INVALID_QUOTE:<label>` |
| Duplicate label/maturity or unordered maturity | `DUPLICATE_TENOR:<tenor>`, `DUPLICATE_MATURITY:<tenor>`, `NON_INCREASING_MATURITY:<tenor>` |
| Maturity on/before trade date | `INVALID_MATURITY:<tenor>` |
| Different trade dates | `MULTIPLE_TRADE_DATES` |
| Instrument construction fails | `INVALID_INSTRUMENT:<tenor>` |
| Different effective dates or collapsed/unordered payment pillars | `REFERENCE_DATE_MISMATCH_BETWEEN_QUOTES`, `NON_INCREASING_PILLAR:<tenor>` |
| Calendar coverage absent or insufficient | `CALENDAR_COVERAGE_UNSPECIFIED` / `CALENDAR_COVERAGE_INSUFFICIENT` |
| Curve reference date / pillars differ from input instruments | `CURVE_REFERENCE_DATE_MISMATCH` / `CURVE_PILLAR_DATES_MISMATCH` |
| Actual curve class is not cubic | `BASELINE_CURVE_TYPE_MISMATCH` |
| Stored calibration tenor order differs | `CALIBRATION_CHECK_TENOR_MISMATCH` |
| Repricing raises a domain/numerical exception | `REPRICING_FAILED` |

Existing solver, method, count, discount-factor and repricing issue codes remain.
Structural tests cover count, date ordering and factor validity before valuation.
A returned non-finite repricing error retains the per-tenor issue code and yields
an infinite aggregate maximum. A skipped or failed repricing also has an infinite
maximum and no checks; it cannot be interpreted as a zero-error fit.

Custom acceptance tolerances must be finite and satisfy `0 <= PASS < FAIL`.
Invalid tolerance configuration raises ValueError rather than returning a curve
rejection. Forward diagnostics, sensitivity, known-truth recovery and authenticity
of data sources remain outside automatic acceptance.

## Manual CLI modes

See [CLI workflows](cli.md): `rebuild` recalibrates explicit inputs; `snapshot`
reassesses persisted nodes without calibration. Neither publishes artifacts.
