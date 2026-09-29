# Baseline execution archives and publication

Stage 5 introduces artifact schema `2.0`. The exporter is independent of the CLI:

```python
from yield_curves.snapshots import export_baseline_snapshot, resolve_current_snapshot

exported = export_baseline_snapshot(
    result=result, dataset=dataset, calendar=calendar, output_root="outputs/baseline"
)
print(exported.run_id, exported.run_path, exported.published)
current_run = resolve_current_snapshot("outputs/baseline")
```

Pass the dataset and calendar that produced the result. The exporter checks
accepted-result consistency and matches input tenors/rates to independent
repricing checks. The caller remains responsible for supplying the original
calendar and dated input objects; an accepted result does not retain their full
identity internally. The exporter does not reread potentially changed source files.

## Layout and schema migration

```text
outputs/baseline/
  current.json
  runs/<unique-run-id>/
    input_quotes.csv
    calendar.json
    curve_nodes.csv
    quote_repricing.csv
    metadata.json
    manifest.json
```

`current.json` identifies exactly one accepted run and fingerprints its manifest.
The manifest identifies the run, acceptance state, schema version and SHA-256 of
each of the five payload files. A rejected run has its own manifest and remains
available for inspection, but does not update the current pointer. With no prior
accepted run, rejection leaves no `current.json`.

The old three flat files are schema `1.0` historical snapshots. They are left
untouched and are no longer updated by the script. Consumers must migrate to
resolving `current.json`; there is no automatic fallback to potentially stale
flat files. These artifacts remain an audit interface. Arbitrary-date pricing
continues to use the Python curve object.

## Contents and provenance

- `input_quotes.csv`: exact normalized calibration fields in their original order.
- `calendar.json`: supplied calendar name, inclusive coverage, weekends, full
  holiday dates and provided/projected provenance.
- `curve_nodes.csv`: tenor, pillar date, discount factor and continuous zero rate.
  A missing curve produces a header-only file. Structurally invalid curves do not
  trigger zero-rate evaluation when archived.
- `quote_repricing.csv`: tenor, input/model quote, signed bp error and status.
  It may be header-only when repricing was skipped. Version 2 omits the old
  index-derived pillar column; nodes are recorded separately.
- `metadata.json`: UTC capture time, unique run identifier, actual interpolation
  method, baseline identity/approach, projection/discount assumption, declared
  quote provenance and original source-file SHA-256, solver diagnostics,
  acceptance with both effective tolerances, and Python/package versions.
- `manifest.json`: checksums bind the normalized inputs, calendar and results into
  one complete execution archive.

The source CSV fingerprint describes original bytes; `input_quotes.csv` describes
the parsed values actually supplied. Unknown or non-finite diagnostics are JSON
`null` / CSV empty fields, never nonstandard JSON `NaN` or `Infinity`. Issue codes,
acceptance state and the encoding declaration preserve the meaning of a rejected
or unpriced result.

## Publication and failure behavior

Files are written and flushed in a unique staging directory on the same filesystem
as `runs/`. After all files and the manifest are complete, the directory is renamed
to its permanent run ID. For an accepted result only, a temporary pointer is
written/flushed and atomically replaces `current.json` with `os.replace`.

Before the pointer replacement, readers continue to resolve the previous run.
Afterward they resolve the complete new run. `resolve_current_snapshot` reads the
pointer once, verifies its schema/run identity, the manifest and every payload
checksum, and returns that run's path. It does not reconstruct a Python curve.
Missing files and corruption raise errors instead of silently falling back.

An ordinary serialization/write failure cleans up this execution's staging files.
A pointer replacement failure preserves the previous pointer and leaves the
complete new run as an unpublished archive. A process killed before cleanup can
leave hidden `.staging-*` or `.current-*.tmp` files; readers ignore them. Existing
run directories are never overwritten or pruned by this API.

The implementation targets local POSIX filesystems supporting directory fsync
and atomic same-filesystem rename. It flushes files and directories. It is not a
distributed transaction or a guarantee against storage hardware failures. The
pointer replacement is the commit point: a subsequent directory-fsync error may
raise after a complete new run has already become current. It cannot expose a
mixture of run files. Concurrent accepted writers follow last pointer replacement
wins; the exporter does not impose valuation-date ordering. Run immutability is
a library convention, not filesystem access control.

## Current CLI integration

The operational script requires explicit quotes, classification, source, holiday
CSV, calendar coverage/source and output destination. The separate demo owns
synthetic/projected defaults. See [CLI workflows](cli.md) for full commands and
the `rebuild` and `snapshot` assurance modes. `build_snapshot` still returns a
`BaselineResult`, but now takes loaded `dataset`, `calendar` and `output_root`.

Invalid inputs that fail before producing a `BaselineResult` propagate their
exception and produce no run archive. Export/publication errors also propagate.
The CLI returns 1 for an archived rejected result and 0 for an accepted published
result. Publication does not change calibration or acceptance policy.

## Tests

`tests/unit/test_snapshots.py` exercises accepted/rejected runs, missing curves,
strict JSON, input mismatch, checksum corruption, failures at each file write,
pointer replacement failure, readers at the commit boundary, actual tolerance
metadata and the operational script using a temporary output directory.
