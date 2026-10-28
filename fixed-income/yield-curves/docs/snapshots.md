# Baseline execution archives and publication

The current artifact schema is `3.0` (`SCHEMA_VERSION` in
`yield_curves.snapshots`). Publication consumes a completed `ExecutionEnvelope`,
issued by the execution workflow rather than assembled from an existing result:

```python
from yield_curves.execution import build_baseline_execution
from yield_curves.snapshots import export_baseline_snapshot, resolve_current_snapshot

execution = build_baseline_execution(
    dataset=dataset,
    calendar=calendar,
)

exported = export_baseline_snapshot(
    execution=execution,
    output_root=output_root,
)
print(exported.run_id, exported.run_path, exported.published)
if exported.published:
    current_run = resolve_current_snapshot(output_root)
```

The caller supplies the loaded quote `dataset`, the covered business `calendar`
and an explicit `output_root`. This is an API example with caller-owned objects;
see [CLI workflows](cli.md) and the [README Quickstart](../README.md#quick-start)
for runnable checkout commands, including the synthetic/projected demo.

## Execution identity and publication authority

`build_baseline_execution` captures an execution ID, UTC capture time and source
provenance before building. It prepares immutable financial inputs: ordered quote
values, common reference date, expected payment-date pillars and the calendar's
name, inclusive coverage, weekends and complete holiday set. H01 canonical tenor
identity strips outer whitespace before duplicate checks and value capture; it
does not otherwise reinterpret tenor labels. Caller objects remain unchanged.

Quote and calendar source provenance stay separate from this financial identity.
CSV adapters hash and parse the same source bytes. The execution copies source
path/hash/classification declarations before calibration; publication does not
reread source files. In-memory inputs may have UNKNOWN provenance with no source
path/hash, and calendar provenance may be absent. These declarations and hashes
do not authenticate a source or certify market data/calendar completeness.

The baseline result retains financial context: prepared inputs and the selected
construction policy, including conventions, curve geometry and acceptance policy.
Acceptance binds the assessed inputs, context, curve values and spline state,
solver declarations and policy. The execution fingerprint additionally binds
provenance and historical acceptance. Publication revalidates these bindings and
the supported policy before writing. Changes to bound values are rejected.

Standard publication requires this execution envelope and the supported standard
V1 acceptance policy. An isolated assessment does not establish construction
history or publication authority. Explicit tolerance overrides select custom
analysis, even when numerically equal to the standard values; custom acceptance
cannot be published through this exporter. Accepted publication additionally
requires solver success, valid structure, nonempty finite independent repricing,
no issues and every check PASS. REVIEW is rejected.

## Layout and supported schema

Under the caller's `output_root`:

```text
  current.json
  runs/<unique-run-id>/
    input_quotes.csv
    calendar.json
    curve_nodes.csv
    quote_repricing.csv
    metadata.json
    manifest.json
```

`current.json` identifies exactly one accepted run, its execution binding and its
manifest's byte checksum. The manifest identifies the run, acceptance state,
schema and SHA-256 of each of the five payload files. A rejected standard execution
also receives a complete archive but never updates the pointer. With no prior
accepted run, rejection leaves no `current.json`.

The old three flat files (`curve_nodes.csv`, `quote_repricing.csv`, `metadata.json`)
are schema `1.0` historical snapshots, archived together under
`outputs/baseline/legacy/schema-1.0/` with their exact bytes and original metadata
preserved. No UUID, manifest, binding or current pointer was added. They are never
promoted or used as fallback by the resolver or snapshot assurance. An absent
pointer is an error even when that legacy archive exists. Only bound schema `3.0`
is supported; earlier and unknown schemas are rejected, without implicit migration.
These artifacts remain an audit interface; arbitrary-date pricing uses the Python
curve object.

## Contents and integrity

- `input_quotes.csv`: normalized calibration fields in their original order,
  including canonical tenors, dates and parsed rates.
- `calendar.json`: captured calendar values and separate provided/projected provenance.
- `curve_nodes.csv`: tenor, pillar date, discount factor and continuous zero rate.
  A missing curve produces a header-only file. Structurally invalid curves do not
  trigger zero-rate evaluation when archived.
- `quote_repricing.csv`: tenor, input/model quote, signed bp error and status.
  It may be header-only when repricing was skipped. Pillars are recorded separately
  in the node file.
- `metadata.json`: run creation time, execution capture record, financial context,
  baseline/construction identity, interpolation, solver diagnostics, historical
  acceptance and its policy/tolerances/binding, source provenance, environment
  versions and value fingerprints.
- `manifest.json`: exact-byte payload checksums and execution binding.

Raw-file SHA-256 checksums cover exact serialized artifact bytes; a source-file
checksum covers original source bytes when available. Value fingerprints hash
sorted compact UTF-8 JSON representations of the execution, financial context,
payload binding and acceptance. The payload binding uses hexadecimal floats for
exact numeric identity, including spline and diagnostic state. Normal artifact
diagnostics encode unavailable/non-finite values as JSON `null` / CSV blank,
never nonstandard JSON `NaN` or `Infinity`.

These checks detect inconsistent values or bytes, not deliberate forgery or source
authenticity. Exact binding and historical comparisons also do not promise universal
bitwise numeric replay across Python/NumPy/SciPy environments.

## Publication and failure behavior

Execution/input validation happens before archive writes. Invalid inputs that fail
before producing a baseline result raise without a run archive; export validation
errors also precede writes. A completed rejected standard execution can be archived.
Publication does not recalibrate or change acceptance policy.

Files are written and fsynced in a unique staging directory on the same filesystem
as `runs/`. Once payloads and manifest are complete and the staging directory has
been fsynced, it is renamed to the permanent run ID and `runs/` is fsynced. For an
accepted result only, a temporary pointer is written/fsynced and atomically replaces
`current.json` with `os.replace`, followed by an output-root directory fsync.

The pointer replacement is the publication commit point. Before it, readers resolve
the previous run; afterward, they resolve the complete new run. An error before the
run-directory rename removes this execution's staging files during ordinary cleanup.
An error after that rename can leave a complete unpublished archive. A pointer-write
or replacement failure preserves the previous pointer. A directory-fsync error
**after successful pointer replacement** can raise when the new run is already
current: no rollback is promised after that commit. A raised export exception
therefore does not necessarily mean that publication did not occur.

A process killed before cleanup can leave hidden `.staging-*` or `.current-*.tmp`
files; readers ignore them. Existing run directories are never overwritten or
pruned by this API. Cleanup of abandoned files is not automatic.

The implementation targets local POSIX filesystems supporting directory fsync and
atomic same-filesystem rename. It does not provide distributed transactions or a
guarantee against storage hardware failures. Atomic pointer replacement does not
expose a mixture of run files. Concurrent accepted writers follow last pointer
replacement wins; no valuation-date ordering is imposed. Run immutability is a
library convention, not filesystem access control.

## Resolution and snapshot assurance

`resolve_current_snapshot` reads the pointer once, validates schema/run identity,
manifest checksum and inventory, every payload checksum, accepted metadata and
execution fingerprint, and returns that complete run's path. It does not reconstruct
a curve. Missing files, corruption and unsupported schemas raise; there is no
fallback to another run or legacy files.

`assess_current_snapshot`, exposed by the assurance CLI's `snapshot` subcommand,
resolves a supported bound archive and verifies stored baseline-policy identity and
`FTIIE_STANDARD_BASELINE_ACCEPTANCE_V1`, including its PASS `0.01` bp and FAIL
`0.10` bp tolerances. It decodes the supported historical construction policy rather
than supplying missing identity or silently adopting a different current policy.
Unsupported historical policies and schemas fail explicitly.

Assurance rebuilds financial inputs from archived quotes/calendar and reconstructs
the cubic curve from stored dates and discount factors **without solving**. It
checks context, provenance, node values, solver declarations and payload/acceptance
bindings; independently checks structure and reprices using those same supported V1
rules; and compares fresh acceptance and repricing with historical evidence and the
repricing CSV. Historical evidence is preserved. Stored solver success is a
historical declaration, not a repeated optimization. Assurance performs no writes,
exports or publication.

The operational helper `build_snapshot(dataset=..., calendar=..., output_root=...)`
returns a `BaselineResult`. The CLI requires explicit inputs and output destination;
only the separate demo owns synthetic/projected defaults. It returns 1 for an
archived rejected result and 0 for an accepted published result. Export/publication
exceptions propagate, subject to the commit-point semantics above.

## Tests

`tests/unit/test_snapshots.py` covers accepted/rejected archives, execution and H01
identity, publication authority, strict JSON, integrity and binding mismatches,
unsupported policies/schemas, legacy exclusion, failures around run/pointer commits,
and assurance without solver calls or writes. CLI integration uses temporary output
directories.
