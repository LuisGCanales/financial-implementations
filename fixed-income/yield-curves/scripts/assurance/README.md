# Baseline Assurance — Rebuild or Snapshot

[`validate_baseline_curve.py`](validate_baseline_curve.py) offers **two read-only assessment modes**. Neither mode exports runs, modifies snapshots, or promotes a result.

| Mode | What it checks | Runs calibration? |
|---|---|---|
| `rebuild` | Rebuilds the selected baseline from supplied quotes/calendar and reports standard acceptance | **Yes** |
| `snapshot` | Verifies an existing supported archived run, reconstructs its persisted curve, and independently reprices OIS quotations | **No** |

## Rebuild from explicit inputs

```bash
python scripts/assurance/validate_baseline_curve.py rebuild \
  --quotes my_quotes.csv \
  --classification OBSERVED_MARKET_DATA \
  --source "Quote provider and valuation date" \
  --calendar holidays.csv \
  --calendar-start 2026-01-01 \
  --calendar-end 2057-12-31 \
  --calendar-source "Holiday provider and version"
```

This performs a **fresh calibration** and acceptance assessment but does not archive or publish the result.

## Assess the current persisted snapshot

```bash
python scripts/assurance/validate_baseline_curve.py snapshot \
  --output-root outputs/baseline
```

This verifies the accepted run referenced by `current.json`, including its **schema 3.0** integrity and stored standard-policy identity. It reconstructs the natural-cubic curve **from saved discount-factor nodes**, checks financial context and bindings, and repeats independent OIS repricing **without running the optimizer**.

The stored original solver status is not a new solver result. Archive fingerprints establish **integrity**, not authenticity of underlying market data.

Normal acceptance returns code `0`; rejection returns `1`. Invalid arguments use `argparse` exit `2`; missing/corrupt inputs or other errors may terminate with a nonzero exception.

[CLI instructions](../../docs/cli.md) · [Validation and rejection](../../docs/validation.md) · [Snapshot assurance contract](../../docs/snapshots.md)

For creating **new test reference candidates** (a different developer activity), see [`../tests/`](../tests/README.md). Experimental sequential-bootstrap reports are under [`../experiments/bootstrap/`](../README.md#2-sequential-bootstrap-repricing-and-curve-diagnostics), with distinct acceptance meaning.
