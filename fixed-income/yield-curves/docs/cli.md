# Baseline command-line workflows

Stage 6 separates explicit operational inputs, manual assurance and the synthetic demo.
Run these commands from the project root after installing the package.

## Operational build

All inputs and the destination are required:

```bash
python scripts/operational/build_baseline_curve.py \
  --quotes my_quotes.csv --classification OBSERVED_MARKET_DATA \
  --source "Quote provider and valuation date" \
  --calendar holidays.csv --calendar-start 2026-01-01 --calendar-end 2057-12-31 \
  --calendar-source "Holiday provider and version" \
  --output-root outputs/baseline
```

Quotes use the [general CSV contract](input_contract.md). Classification must be
`SYNTHETIC_REFERENCE_DATA`, `OBSERVED_MARKET_DATA` or `UNKNOWN`, consistent with any
CSV `data_class`. Calendar CSVs have a `date` column containing ISO holiday dates;
a header-only CSV explicitly declares no holidays beyond weekends. Coverage is
inclusive, declared by the caller, and must include observation and payment dates.
The provided-calendar label is provenance, not certification of completeness.
The CLI does not generate projected holidays or infer coverage from holiday extrema.

The script exports each result and publishes accepted runs as described in
[snapshots.md](snapshots.md). Its Python helper now takes `dataset`, `calendar`
and `output_root`; the public baseline Python API is unchanged.

## Manual assurance

These modes never publish, export or modify the input snapshot.

To calibrate from inputs again, use `rebuild` with the same seven input flags as
above (omit `--output-root`):

```bash
python scripts/assurance/validate_baseline_curve.py rebuild \
  --quotes my_quotes.csv --classification OBSERVED_MARKET_DATA \
  --source "Quote provider and valuation date" \
  --calendar holidays.csv --calendar-start 2026-01-01 --calendar-end 2057-12-31 \
  --calendar-source "Holiday provider and version"
```

To assess the persisted current run without running calibration:

```bash
python scripts/assurance/validate_baseline_curve.py snapshot --output-root outputs/baseline
```

Snapshot mode resolves the pointer once, checks hashes and baseline identity,
reconstructs the cubic curve from persisted dates and discount factors, and
repeats structural checks and independent repricing using the archived quotes
and calendar. It applies the **current default baseline acceptance tolerances**;
the original tolerances remain in metadata for audit. Stored solver success is a
historical declaration, not an independently repeated optimization. Hashes check
integrity, not authenticity. This mode validates a published accepted run; it
does not load legacy flat files or select unpublished/rejected runs.

Both modes return 0 for accepted and 1 for rejected assessments. Missing CLI
arguments return 2. Invalid files, integrity failures, insufficient coverage
before calibration and I/O errors raise exceptions with a nonzero process exit;
they do not publish a new current run. Automatic in-memory acceptance still
occurs whenever the public baseline build API runs; this manual script is not
called by that API or the operational builder.

## Explicit synthetic demo

```bash
python scripts/demo/build_synthetic_baseline.py
python scripts/assurance/validate_baseline_curve.py snapshot --output-root outputs/demo/baseline
```

The demo alone selects the frozen synthetic CSV and projected 2026–2057 calendar.
Its default destination is `outputs/demo/baseline`, separate from operational
outputs. `--output-root` overrides that destination explicitly.

## Migration

The former no-argument operational and assurance commands are replaced by the
explicit demo and the assurance subcommands above. No operational default paths,
synthetic datasets or projected calendars remain in those two entrypoints.
Historical flat outputs and the numerical reference fixture are unchanged.
