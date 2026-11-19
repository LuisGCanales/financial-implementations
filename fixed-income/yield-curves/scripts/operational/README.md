# Operational Baseline Builder

[`build_baseline_curve.py`](build_baseline_curve.py) constructs and archives an **MXN F-TIIE OIS curve** using caller-supplied par quotations and a business calendar. It uses the project's **selected simultaneous/natural-cubic baseline** and runs the standard input and acceptance checks.

It does **not** choose synthetic quotes, generate projected holidays, or change the selected interpolation method implicitly.

## Run

From `fixed-income/yield-curves` with Python 3.11 and the editable project installation:

```bash
python scripts/operational/build_baseline_curve.py \
  --quotes my_quotes.csv \
  --classification OBSERVED_MARKET_DATA \
  --source "Quote provider and valuation date" \
  --calendar holidays.csv \
  --calendar-start 2026-01-01 \
  --calendar-end 2057-12-31 \
  --calendar-source "Holiday provider and version" \
  --output-root outputs/baseline
```

All inputs and the destination are **required**. The dates in this example describe **declared calendar coverage**, not proof that `holidays.csv` contains a complete verified calendar through 2057. Similarly, declaring observed quotations is **not independent data authentication**.

## Outputs and publication

The builder captures the input financial values and source provenance in an execution envelope, calibrates, and evaluates the baseline, then writes a run archive under the supplied `--output-root`.

**Only an accepted standard run is promoted** through `current.json`. A completed rejected run may be archived without becoming current; input failures before calibration can raise without an archive.

A successful process exit reports acceptance; publication has additional documented failure semantics, including the possibility of an exception **after** the accepted pointer has changed.

[Complete command reference](../../docs/cli.md) · [Input requirements](../../docs/input_contract.md) · [Snapshot contract](../../docs/snapshots.md)

For an explicit frozen synthetic demonstration, use [`../demo/build_synthetic_baseline.py`](../demo/README.md), not the operational builder's input defaults.
