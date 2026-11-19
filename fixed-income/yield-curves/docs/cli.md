# Command-Line Workflows — Calibration and Assurance

Repository scripts provide **three deliberately separate workflows**: construction and archival from explicit inputs, manual validation without publishing, and a self-contained synthetic demonstration. They use the **selected simultaneous/natural-cubic baseline**, not an automatically chosen alternative interpolation method.

Run commands from the `fixed-income/yield-curves` directory in a checkout with **Python 3.11** and the project installed:

```bash
cd fixed-income/yield-curves
python -m pip install -e '.[dev,plots]'
```

See the [project README](../README.md#reproducibility) for a virtual-environment setup.

## Which command should I use?

| Goal | Entry point | Recalibrates? | Writes or publishes? |
|---|---|---|---|
| Build a baseline with caller-supplied inputs | `scripts/operational/build_baseline_curve.py` | Yes | Archives a complete standard result; **promotes only if accepted** |
| Validate a fresh construction without publication | `scripts/assurance/validate_baseline_curve.py rebuild` | Yes | **No writes** |
| Check an existing accepted snapshot | `scripts/assurance/validate_baseline_curve.py snapshot` | **No** | **No writes** |
| Run the frozen research demonstration | `scripts/demo/build_synthetic_baseline.py` | Yes | Archives the synthetic run; **promotes only if accepted** in its demo destination |

The ordinary Python API has its own in-memory acceptance path; **manual assurance is not a prerequisite** for calling `build_baseline_ftiie_curve()`.

## 1. Build from explicit quotes and calendar

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

**All seven input declarations and the output destination are required:** quote CSV, classification, quote source, holiday CSV, start/end coverage, and calendar source. The script does not silently load the frozen synthetic quotes or a projected future calendar.

`OBSERVED_MARKET_DATA` is a **caller declaration**, not a verification that `my_quotes.csv` contains authentic market observations. Likewise, declaring calendar coverage through 2057 requires a genuinely appropriate dataset; the CLI does not generate or certify those future holiday dates.

Inputs are documented in the [quote/calendar contract](input_contract.md). Financial preflight checks instrument dates, calendar coverage, quotes, and increasing payment pillars before calibration.

The builder creates an execution envelope with captured financial inputs and source declarations, calibrates the curve, performs standard acceptance, and archives the completed run. **Only accepted executions** replace `current.json` at the destination.

## 2. Rebuild and assess without publishing

Recalibrate explicit quotes and a supplied calendar, then print acceptance diagnostics:

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

This **runs calibration again** and performs standard in-memory acceptance; it does **not** export a new snapshot or change the current published run.

Alternatively, inspect the **persisted accepted run** without a solver:

```bash
python scripts/assurance/validate_baseline_curve.py snapshot \
  --output-root outputs/baseline
```

Snapshot mode resolves `current.json` once, checks the supported **schema 3.0** archive, its manifests, hashes, stored financial inputs, policy identity, and acceptance bindings, then reconstructs the persisted **natural-cubic curve** from its nodes and independently reprices the archived OIS.

This is **not a recalibration**: it does not solve for new discount factors, reinterpret older policies under a new standard, modify archives, or publish a result. The currently supported standard acceptance rules include a **0.01 bp PASS tolerance** and **0.10 bp FAIL threshold**. Unsupported or unbound older schemas are rejected rather than silently migrated.

Saved solver success is an archived declaration, not a repeated optimization. Hash and binding checks establish internal consistency and byte integrity, **not authenticity of externally supplied market data**.

## 3. Reproduce the synthetic demonstration

```bash
python scripts/demo/build_synthetic_baseline.py \
  --output-root outputs/demo/baseline

python scripts/assurance/validate_baseline_curve.py snapshot \
  --output-root outputs/demo/baseline
```

The demo explicitly selects the **frozen synthetic F-TIIE OIS quotations** and a **projected 2026–2057 MXMC calendar**. Its output root defaults to `outputs/demo/baseline`; passing `--output-root` overrides it.

Unlike an ordinary operational invocation, the demo intentionally uses known synthetic research inputs. Its results do **not** establish observed-market calibration or certified future MXMC holidays.

[Research scenario](../data/synthetic/README.md) · [Calendar data](../data/calendars/README.md)

## 4. What is saved?

Under the chosen output root, an accepted run is addressed through `current.json`:

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

A **completed rejected** standard execution can leave a full run archive without changing the accepted pointer. Invalid inputs that fail before an execution result is produced do not yield an archive.

The export process publishes the pointer through an atomic replacement after writing a complete run. **An error after pointer replacement can occur even when the new accepted run is already current**; a nonzero process exit does not by itself prove that publication was rolled back. See the full [snapshot failure semantics](snapshots.md#publication-and-failure-behavior).

## 5. Return codes and errors

For the assurance modes and ordinary completed runs, `0` indicates accepted and `1` indicates rejected. Missing or invalid command arguments exit through `argparse` with code `2`. File/coverage errors, archive integrity failures, or raised numerical exceptions may instead terminate with a nonzero error before a normal acceptance result is printed.

These CLI scripts do not implicitly select experimental calibration methods. Their role is to build, assess, and optionally archive the selected baseline under explicit inputs.

[In-memory integration](integration_contract.md) · [Acceptance conditions](validation.md) · [Snapshot integrity and publication](snapshots.md)
