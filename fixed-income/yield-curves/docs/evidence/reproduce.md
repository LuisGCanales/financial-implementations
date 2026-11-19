# Reproducing Yield-Curve Research Evidence

This guide explains **what can actually be reproduced from the public repository**, which source files and numerical environment were used in the recorded verification, and how to distinguish **figure regeneration from financial recalibration**.

The evidence comes from a **controlled synthetic F-TIIE OIS experiment** with 15 par quotations, a projected long-horizon MXMC calendar, and same-curve projection/discounting. Reproducing its plotted sensitivities from saved data is **not equivalent to recalibrating the underlying curve**.

[Research evidence](index.md) · [Claim audit register](claims.md) · [Machine-readable evidence index](../../evidence/c03/index.json) · [Saved-input transport manifest](../../evidence/c03/replay-inputs.json)

## Three separate levels

| Level | Objective | What it can establish |
|---|---|---|
| **1 — Inspect public results** | Read the **30 selected CSV/PNG exhibits**, financial narratives, claim registers and manifests | Financial findings and selected source identities **as recorded**; not a full audit or new computation |
| **2 — Replay saved-data consumers** | Verify and extract both global sensitivity input CSVs, then run the heatmap and locality-reporting programs **without calibration** | Recomputed figure/summary results from the saved response matrices in the recorded numerical environment |
| **3 — Recompute financial experiments** | Use the original financial source and frozen synthetic inputs to rerun the **global sensitivity producer** | A **new** calibration and quote-shock execution, requiring a separate comparison; this full rerun was **not performed** in the recorded Level-2 verification |

**Recommended path:** inspect the [financial findings](index.md) first. Use **Level 2** to independently check the saved-data transformations. Choose **Level 3** only when the underlying calibration, numerical solver behavior or sensitivity production itself must be recomputed.

### Verified Level-2 scope

The recorded saved-data validation used the original compressed global response matrices and executed **the heatmap and locality consumers once each** in the reference environment. Both completed successfully; **all 441 saved numeric comparisons matched exactly**, and the two regenerated reference CSVs were byte-identical. That is evidence of **saved-value transformation/replay in the tested environment**, not recreated optimizer history or generalized cross-version byte-for-byte reproducibility.

The **30 public exhibits** are a selected subset (28 original files and two reviewed presentation derivatives). The original complete accepted snapshot, some audit logs and selected original metadata remain external. The two compressed global-sensitivity inputs are **computational dependencies**, not additional public exhibit claims.

The original financial calculation, public-evidence selection and saved-data replay occurred at different times. Their exact revision and file identities appear below. An identifier such as `C04d2` refers to the **archived recorded verification**, not a software feature, required development stage or present-day pull-request status.

## Source and reference environment

Original financial source: `bee31fd0883660f171ebe84817b98641239eae5b`. Consumer source validated in the recorded C04d2 replay: `d9a79eac35a8224ee8633b56b8441d0a53d0a74c`. The heatmap source includes the C04c-F01 presentation correction; original source SHA-256 `c5b62462070a2cd1ac7ba1d51553d6352bbc55b75869fa21d4201d2cc67ce754` differs from current `3c3844dd9f133f88199fd4de1c2d48ede9de499ee1d0dabbcbc612b496a6c4e8`. Locality source is unchanged: `15267683e7a5e6ac3070ebf47c98f1283384b760dcbdc4122110f20fd913088b`.

Measured environment: **Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.11.2, Pillow 12.3.0, yield-curves 0.1.0**; zlib compile/runtime 1.2.11. The transport manifest records installed distribution versions. This is the tested environment, not a cross-version compatibility promise. C04d2 used the existing editable installation, without creating an environment or installing dependencies.

Use a repository checkout containing the saved-data transport files and an existing Python **3.11** environment at the project `.venv`. Keep the complete checkout available for repository scripts and fixtures. From the financial-implementations Git root:

```bash
set -eu
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT/fixed-income/yield-curves"
PROJECT_ROOT=$PWD
PYTHON="$PROJECT_ROOT/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
"$PYTHON" -B -c 'import sys; assert sys.version_info[:2] == (3, 11)'
```

**Environment setup (not part of the recorded fresh-install validation):** provision Python 3.11 and install the checkout editably with plot extras if it is not already installed. Broad package requirements do not pin the reference environment. Editable-build dependencies belong to local setup; the historical measured environment and execution above remain unchanged. For current pinned development setup, see [testing](../testing.md); those pins do not redefine the historical C04d2 reference environment.

```bash
"$PYTHON" -B -m pip install -e '.[plots]'
```

## Immutable transport and original inputs

The verified source identities are the original archived response datasets under `C03b2a/full-global-root/tables/07_global_sensitivity/`. This is an **archival path**, not a current location that the reader must create; the replay procedure restores the raw files to their **actual consumer paths** from the public compressed assets. Scenario **FTIIE_KNOWN_TRUTH_V1**, reference **2026-09-18**, frozen synthetic quotes (trade 2026-09-15), projected MXMC 2026–2057 and same-curve projection/discounting. Three methods: LOG_LINEAR_DF, LINEAR_CONTINUOUS_ZERO, CUBIC_CONTINUOUS_ZERO. Fifteen quote indices 0–14 map to 1M, 2M, 3M, 6M, 9M, 1Y, 2Y, 3Y, 4Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y. Shocks are symmetric ±1 bp; `bump_bp=1.0` is the magnitude.

| Raw filename | gzip bytes | Raw bytes / data rows |
| --- | ---: | ---: |
| global_forward_sensitivity_dense.csv | 2,596,444 | 13,313,113 / 70,290 |
| global_node_sensitivity_long.csv | 16,412 | 84,886 / 675 |

Forward gzip SHA-256: `d4de8b882703c2190568c8bb77df9ec043b5bba89da74d00640f84fd9b3a478f`.
Forward raw SHA-256: `25cc79642af8acc9c6f8ddabdaaa0d10c6c7282274b36c2695032abdbeab6a40`.

Node gzip SHA-256: `7e7860ebc64bad3246c40dea15f9bbc595e4eb30e9e32f7eec6401c07b299faf`.
Node raw SHA-256: `8ab114ac102b6ff382d96d69a2b32101515f5da6f12f41a2c6db563984f63e1c`.

The two [gzip inputs](../../evidence/c03/replay-inputs/) are computational dependencies, not new curated financial exhibits. Each was independently compressed twice outside Git with Python `gzip.GzipFile`, `compresslevel=9`, `filename=""`, `mtime=0`. Repeated bytes matched the approved identities; header `1f8b08000000000002ff` has no original name, comment, extra field or source timestamp. A separate binary decompression recovered exact original bytes, CRLF, ordering and numeric text precision. Do not parse/reserialize CSVs to extract them. Different compressors may yield different gzip bytes; the bundled identities and raw hashes are the gate.

## Validated Level-2 procedure

Create a fresh external root, including separate reports, temp, Matplotlib cache, logs and validation destinations. Keep the root for review. Never point at the historical archives or curated exhibit directory. These setup/extraction operations and CLI arguments were executed in C04d2 through the external harness; variable names below make the paths portable.

```bash
REPLAY_BASE=$(mktemp -d "${TMPDIR:-/tmp}/c04-replay.XXXXXXXX")
REPORTS_ROOT="$REPLAY_BASE/reports"
export REPLAY_BASE REPORTS_ROOT
export TMPDIR="$REPLAY_BASE/tmp"
export MPLCONFIGDIR="$REPLAY_BASE/matplotlib"
export MPLBACKEND=Agg
mkdir -p "$REPORTS_ROOT" "$TMPDIR" "$MPLCONFIGDIR" "$REPLAY_BASE/logs" "$REPLAY_BASE/validation"
```

Run this inline extractor from the project directory. It checks both archive identities and recovered raw identities before creating either input, refuses existing destinations and fixes the consumer layout explicitly. A C04d2 controlled incorrect-checksum test failed before any raw write or consumer execution; original assets were unchanged.

```bash
"$PYTHON" -B - <<'PYTHON'
import gzip
import hashlib
import json
import os
from pathlib import Path

project = Path.cwd().resolve()
root = Path(os.environ['REPORTS_ROOT']).resolve()
if root.is_relative_to(project.parents[1]):
    raise ValueError('Use a new reports root outside the repository')
entries = json.loads(Path('evidence/c03/replay-inputs.json').read_text())['inputs']
allowed = {'global_forward_sensitivity_dense.csv', 'global_node_sensitivity_long.csv'}
if len(entries) != 2 or {e['raw_filename'] for e in entries} != allowed:
    raise ValueError('Unexpected input inventory')
verified = []
for entry in entries:
    name = entry['raw_filename']
    relative = 'tables/07_global_sensitivity/' + name
    if entry['archive_path'] != 'evidence/c03/replay-inputs/' + name + '.gz':
        raise ValueError('Unexpected archive path')
    if entry['required_consumer_relative_path'] != relative:
        raise ValueError('Unexpected consumer path')
    packed = Path(entry['archive_path']).read_bytes()
    if len(packed) != entry['compressed_bytes'] or hashlib.sha256(packed).hexdigest() != entry['compressed_sha256']:
        raise ValueError('Compressed input integrity failure: ' + name)
    raw = gzip.decompress(packed)
    if len(raw) != entry['raw_bytes'] or hashlib.sha256(raw).hexdigest() != entry['raw_sha256']:
        raise ValueError('Raw input integrity failure: ' + name)
    target = root / relative
    if not target.resolve().is_relative_to(root) or target.exists():
        raise ValueError('Unsafe or existing destination: ' + name)
    verified.append((target, raw, entry['raw_sha256']))
# Both inputs are verified before either can be read by a consumer.
for target, raw, expected in verified:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError('Written input integrity failure')
PYTHON
```

Both inputs must share exactly this reports root:

```text
REPORTS_ROOT/
  tables/07_global_sensitivity/
    global_forward_sensitivity_dense.csv
    global_node_sensitivity_long.csv
```

The real current `read_dense_forward_sensitivity`, `read_pillar_years` and `load_locality_results` were imported without executing their main CLI and called on the recovered pair. Empty explicit roots and roots missing either required input raised `FileNotFoundError` as appropriate, with no fallback to historical checkout data. Always supply `--reports-root`; omission selects the historical default.

Run the actual consumers sequentially, stopping on any nonzero exit:

```bash
"$PYTHON" -B scripts/experiments/sensitivity/plot_global_forward_sensitivity_heatmaps.py \
  --reports-root "$REPORTS_ROOT" > "$REPLAY_BASE/logs/heatmaps.stdout.log" 2> "$REPLAY_BASE/logs/heatmaps.stderr.log"
"$PYTHON" -B scripts/experiments/sensitivity/report_forward_sensitivity_locality.py \
  --reports-root "$REPORTS_ROOT" > "$REPLAY_BASE/logs/locality.stdout.log" 2> "$REPLAY_BASE/logs/locality.stderr.log"
```

Each CLI was executed exactly once and exited 0 in C04d2. Their call paths read persisted CSVs and use plotting/reporting and saved-value arithmetic, without financial calibration. Logs and generated metadata may contain the new absolute temporary paths; retain them externally.

## Expected outputs and comparison gate

| Directory below REPORTS_ROOT | Expected files |
| --- | --- |
| figures/07_global_sensitivity | 12 heatmap PNG/SVG (three methods × two common scales × two formats); eight locality PNG/SVG for RMS distance, spread, center offset and ±2Y mass |
| tables/07_global_sensitivity | Two recovered input CSVs; `forward_sensitivity_heatmap_scale_diagnostics.csv` (four data rows); `forward_sensitivity_locality.csv` (45 data rows) |
| metadata/07_global_sensitivity | `forward_sensitivity_heatmap_metadata.json`; `forward_sensitivity_locality_metadata.json` |
| text/07_global_sensitivity | `forward_sensitivity_locality_report.txt` |

Expected total: **27 files**, including both inputs. C04d2 verified nonempty outputs, decoded all ten PNGs, parsed all ten SVGs, validated CSV headers/counts and both JSONs, checked metadata paths stay inside the temporary reports root, and verified original input hashes after each consumer.

Compare H01 [reference scale diagnostics](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_scale_diagnostics.csv) by **scope + method**, and L01 [reference locality](../../evidence/c03/locality/forward_sensitivity_locality.csv) by **method + shock_index**. Require identical headers, unique complete key domains, scenario/reference/tenor strings and observation counts. Parse saved numeric text as Decimal and require **exact saved-value equality** in this reference environment; report every mismatched key, column and delta. Do not silently add tolerances. Both comparisons passed in C04d2, including byte-identical regenerated CSVs.

The restored source has **45 method/shock groups**, **1,562** weekly forward starts per group (2026-09-18 to 2056-08-18), **15×1,562 matrices per method**, and **675** node responses (15 per shocked quote). Reader matrix values and original pillar mapping were exact. Expected common robust cap is **11.33194135019177 bp/bp**, full cap **20.04398642012309 bp/bp**, cubic robust clipping **0.015023474178403756**, and full-scale clipping **0.0**. The 30Y payment pillar (2056-09-20) lies outside the saved forward-start domain; its marker is omitted while its complete response row remains.

H03/H04 in the public exhibit directories remain the approved C04c-F01 presentation derivatives. Their rendering source was uncommitted at historical rendering time, as preserved by the original manifest. New C04d2 renders have separate execution/byte identities and remain external. PNG/SVG byte equality with historical C03 or approved derivatives is not required; saved numerical identity is required.

## Optional Level 3 — not executed

The historical global producer command is `scripts/experiments/sensitivity/report_global_sensitivity.py --reports-root <new-root>`, recorded in external `C03b2a/metadata/full-producer.json` (SHA-256 `838059712718ee347b3bf88de61e8a4aced103ccbd553ec7bb6f19111da0789a`). Historical heatmap/locality commands used the same explicit reports root; their receipts are `C03b2a/metadata/full-heatmaps.json` (`374d288c83c2a9ebcf6301c5428a966035c81cd21d2175415acb89d429a56689`) and `C03b2a/metadata/full-locality.json` (`c6a2079ca034090332be70b74467e11d9dabe16d39f23ab61cc6d2c3cdbf48b1`). These are archival identities, not download links or C04d2 receipts.

For optional recomputation, use a separate checkout at original financial commit `bee31fd0883660f171ebe84817b98641239eae5b`, Python 3.11 and its editable environment. Verify the frozen quote CSV SHA-256 `38469f91b95ad5afad4a593a39c791a49e34ca435fc461f88d3b2039b717a5e6` and original projected-calendar source identity in the [methodology/risk manifest](../../evidence/c03/methodology-risk-manifest.json). The producer reads frozen quotes and calls `build_projected_mxmc_calendar(2026,2057)`; I01 is the operational supplied-calendar materialization, not an additional research CLI option.

**Unexecuted optional command**, from that original project checkout with PYTHON pointing to its existing Python 3.11 environment:

```bash
FULL_BASE=$(mktemp -d "${TMPDIR:-/tmp}/c04-full.XXXXXXXX")
FULL_REPORTS_ROOT="$FULL_BASE/reports"
mkdir -p "$FULL_BASE/tmp" "$FULL_BASE/matplotlib"
TMPDIR="$FULL_BASE/tmp" MPLCONFIGDIR="$FULL_BASE/matplotlib" MPLBACKEND=Agg \
  "$PYTHON" -B scripts/experiments/sensitivity/report_global_sensitivity.py \
  --reports-root "$FULL_REPORTS_ROOT"
```

The recorded original producer took **4,802.487169651984 seconds** (about 80 minutes) for three base plus 90 shocked calibrations. Level 2 avoids those solves and does not reproduce optimizer iterations, convergence history, elapsed diagnostics or original execution timestamps. A full recomputation creates a new execution identity and needs separate financial comparisons, excluding elapsed/IDs/paths from numerical identity.

## Remaining limits

The complete accepted operational snapshot and eight retained originals remain withheld, as do original complete comparison/execution receipts. Standalone S03/S05/S06 cannot be passed as a snapshot archive to assurance. Section 05 has no historical golden baseline. Frozen golden reference, quotes, package version 0.1.0, snapshot schema 3.0 and historical policy identifiers remain unchanged.

M05's `plot_three_interpolation_methods.py` is a full research workflow: `main → calibrate_curves → calibrate_ftiie_ois_curve_simultaneously`, then writes the dense interpolation CSV. It is not a saved-data reader. Its original 1,563-row dense CSV remains external (SHA-256 `bc642f52b9b654c5e8274d055adddac89080e2f50738dfed334a175e2a5be87e`); distributing it alone would not enable an existing Level-2 CLI. The global 1,562-start grid is distinct. B07 and other omitted research workflows are outside this replay contract.

No fresh-install, cross-platform/version bitwise, complete-audit, observed-market, monetary portfolio-risk or production-readiness guarantee follows. The recorded Level-2 verification did not run calibration, replace original artifacts, install the project from scratch, create a formal release or deploy a website.
