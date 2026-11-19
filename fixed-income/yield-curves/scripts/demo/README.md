# Synthetic Baseline Demonstration

[`build_synthetic_baseline.py`](build_synthetic_baseline.py) provides a **reproducible example** of the standard F-TIIE OIS baseline using:

- Frozen **synthetic OIS par quotations** from [`data/synthetic/ftiie_ois_quotes_v1.csv`](../../data/synthetic/README.md).
- A **projected 2026–2057 MXMC calendar** for research purposes, not verified future market holidays.
- The same baseline financial calibration and acceptance workflow used by the operational builder.

From `fixed-income/yield-curves`:

```bash
python scripts/demo/build_synthetic_baseline.py \
  --output-root outputs/demo/baseline
```

The output root is **optional** and defaults to `outputs/demo/baseline`. The script creates a run archive with quote/calendar provenance and acceptance diagnostics; it promotes a run through `current.json` **only if accepted**.

To verify its archived accepted result **without recalibrating**:

```bash
python scripts/assurance/validate_baseline_curve.py snapshot \
  --output-root outputs/demo/baseline
```

This is an **explicit synthetic demonstration**, not evidence of observed-market calibration or an official long-horizon calendar.

[CLI workflows](../../docs/cli.md) · [Synthetic scenario](../../data/synthetic/README.md) · [Snapshot outputs](../../docs/snapshots.md)
