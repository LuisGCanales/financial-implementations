# Controlled alpha release verification

`yield-curves 0.1.0` remains a controlled alpha. C06b1 implements verification
infrastructure; its local builds are **UNAPPROVED_LOCAL_PREVIEW**. C06b2 verifies
a separately reviewed immutable post-merge commit. C06c decides release readiness
and any later publication. A PASS receipt from these scripts is a gate outcome,
not publication authority. No script creates tags, Releases or registry uploads.

## Distribution and integration scope

Python metadata admits `>=3.11,<3.12`. The reference verification target is
CPython **3.11.15**, Linux x86_64, glibc **>=2.34** (Ubuntu 24.04), NumPy **2.4.6**,
SciPy **1.17.1**, pytest **9.1.1**, Matplotlib **3.11.2**. The hashed locks select
one binary wheel per dependency for this platform. Other platforms, admitted
minimum versions and future resolver combinations need separate validation;
these pins do not change the public dependency ranges or establish universal
compatibility. Snapshot filesystem support retains its local POSIX limits.

All 38 Python modules in `yield_curves`, `yield_curves.research` and
`yield_curves.tooling` remain installed. The supported integration is the
[baseline Python API](integration_contract.md). There are no installed console
entrypoints. Research/tooling inclusion does not promise that defaults which
search for a checkout will work in an installed environment.

The wheel contains Python modules, matching `.dist-info` metadata and the MIT
license notice. The library sdist contains those modules under `src/`,
`pyproject.toml`, `MANIFEST.in`, `README.md`, `CHANGELOG.md`, `LICENSE`, and the
explicitly reviewed fresh setuptools metadata: `PKG-INFO`, `setup.cfg`, and five
`src/yield_curves.egg-info` files. Fresh backend metadata is checked against
current source; inherited editable metadata is rejected before building.

Both distributions exclude checkout tests/fixtures, scripts, data, config, docs,
evidence, outputs, notebooks, requirements locks, private checkpoints, virtual
environments, caches and historical outputs. The full financial suite therefore
runs against a separate complete source export with an independently installed
wheel. The sdist is library build source, not a research reproduction checkout.
README links refer to checkout documentation; that documentation is not bundled.

Current evidence uses synthetic inputs and projected calendars with known
coverage/source limits. Same-curve MXN F-TIIE OIS remains the baseline. PCHIP is
experimental. There is no live-market or production certification, or support
claim for multi-curve construction, FX basis or XVA. Package version `0.1.0`,
baseline/acceptance policy V1, snapshot schema `3.0` and `FTIIE_KNOWN_TRUTH_V1`
remain independent identities. See [limitations](assumptions_limitations.md).

## Three testing tiers

| Tier | Trigger and contract |
| --- | --- |
| A | Relevant PR/main changes: all 1008 non-slow cases, exact 1035-case collection/partition proof, package and installed-import gates, separate verifier self-tests. |
| B | Manual reviewed SHA and explicit `RUN_27_SLOW_CASES` intent: exactly 27 slow cases in one serial pytest session. No xdist, retry or parallel sensitivity jobs. |
| C | Manual approved SHA/version/tree: clean export, isolated sdist then wheel from sdist, independent archive inventories, RECORD/metadata/license/source checks, strict twine check, separate wheel/sdist consumers and pip checks. |

The existing identities remain **38 test modules / 414 source functions / 1035
cases = 1008 non-slow + 27 slow**. The selection verifier pins SHA-256 identities
of the complete sorted C05/C06a node-ID sets; it also compares every outcome and
JUnit case. Missing phases, substituted cases, failures, skips, xfails, collection
errors and nonzero exits cannot pass. Collection-only receipts explicitly say
`COLLECTION_ONLY`. Missing or interrupted evidence is `INCOMPLETE`; a complete
unsuccessful test attempt is `FAIL`. Raw command, exit, node IDs, JUnit, logs,
elapsed time and Linux child-process maximum RSS/CPU observations are retained.
RSS is a process high-water observation, not a sum of process-tree peaks.

The PR workflow has no workflow-level path filter. Its lightweight scope job uses
a complete Git diff from the Git root (including deleted/renamed paths), matching
`fixed-income/yield-curves/**` and `.github/workflows/**`. Irrelevant PRs require
successful scope proof without Python/dependency setup. `yield-curves-required`
always reports; failed/cancelled/unknown scope or relevant validation fails closed.
Workflow YAML alone does not configure branch protection. Demonstrate real
relevant and irrelevant runs before the owner configures required checks. Merge
queue support would require a separately reviewed `merge_group` design.

The numerical workflow serializes manual attempts without cancelling an active
run. The numerical/release workflows are manual only and need to exist on the default
branch before dispatch is available. Supply the reviewed full 40-character SHA,
independently reviewed project tree object and human review reference. Branch
names and uncommitted worktrees are not approved candidates. PR validation uses
an explicitly separate `PR_VALIDATION_ONLY` receipt context.

## Exact external build and installation procedure

Run from the Git root, using infrastructure whose bytes match the approved
commit. The following is an invocation template, **not an executed release**:

```bash
bash fixed-income/yield-curves/scripts/release/run_release_validation.sh \
  --repo /absolute/path/to/financial-implementations \
  --revision FULL_REVIEWED_40_CHARACTER_COMMIT_SHA \
  --expected-tree INDEPENDENTLY_REVIEWED_40_CHARACTER_PROJECT_TREE_SHA \
  --expected-version 0.1.0 \
  --external-root /tmp/yield-curves-reviewed-attempt \
  --approval HUMAN_REVIEW_REFERENCE --tier C
```

The external root must be new and outside Git. `--help` describes A/B variants.
Obtain the subtree object for review with
`git rev-parse FULL_COMMIT_SHA:fixed-income/yield-curves`; approval must bind both
identities. Passing a review reference records human authorization, it does not
authenticate or generate that authorization. C06b1 must not invoke this against
uncommitted changes as though they were an approved candidate.

The script checks its executed helpers against the approved Git commit before
using them. A standard-library verifier requires the exact commit/tree, compares
the complete archive to tracked Git blobs and canonical Git archive headers/modes, rejects
unsafe paths/types/collisions, then writes verified bytes without using archive
extraction APIs. Tree-object exports use a uniform execution timestamp in Git;
that timestamp is excluded from header comparison, while the actual archive
SHA-256 is retained. It never executes a verifier taken from an unverified archive.

The external layout separates `source/project.tar`, read-only `source/immutable`,
writable `build-src`, full `test-project`, `artifacts`, `envs/tools`, `envs/test`,
`envs/wheel`, `envs/sdist`, build/runtime wheelhouses, consumer working directories,
`results`, `logs`, `tmp`, `caches` and sanitized `public` receipts. Nothing is built
in the immutable export or original checkout. All pip/Python configuration inputs
are sanitized; dependencies download only from the explicit PyPI index. The
CPython ensurepip bootstrap provisions the hash-pinned pip/toolchain in a fresh
external tools environment.

`requirements/release-build.txt` freezes build **1.6.1**, setuptools **79.0.1**,
wheel **0.48.0**, twine **7.0.0**, pip **26.3**, their transitive dependencies and
validation-only PyYAML. `requirements/ci-reference.txt` freezes the reference
test/runtime/plot tuple and its transitive dependencies. Hashes identify reviewed
distribution bytes; they do not establish upstream code trust.

Each lock is downloaded with `--require-hashes --only-binary=:all:` into its own
wheelhouse. The script compares the complete wheelhouse hash set to the lock,
installs tools offline with hashes, then sets `PIP_NO_INDEX=1` and build-only
`PIP_FIND_LINKS`. Default `python -m build -v` creates an sdist followed by a wheel
**from that sdist**, with fresh isolated backend environments. Do not replace it
with `--sdist --wheel`, which builds both directly from source. See the
[build usage contract](https://build.pypa.io/en/stable/how-to/basic-usage.html).

The distribution verifier checks each archive independently and emits exact
inventories, bytes and SHA-256 hashes. Unknown backend files require review;
allowlists are not expanded automatically. `twine check --strict` checks rendering
and metadata, and does not establish financial correctness.

For each fresh consumer, the runtime-only NumPy/SciPy lines are taken from the
reviewed hashed reference lock and installed with `--no-index --require-hashes`.
The candidate hash is checked separately against the distribution receipt. The
explicit local wheel/sdist is then installed with `--no-deps --no-cache-dir`,
**without passing a hashed requirements file as pip constraints**. This avoids
requiring a dependency-lock hash for the local candidate. The sdist installation
keeps PEP 517 build isolation enabled and resolves its backend only from the
separately verified build wheelhouse; verbose logs retain backend selections.
See [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/).

Both consumers run `pip check`, retain install reports/inspect/freeze, and execute
the exact C05b public example (SHA-256
`f276abc9a06af5bfceda88db9b1612aa7903462975ce685a6a54c7c326983ea6`)
from independent working directories with `python -I -B`. Smoke checks cover
site-packages origins, non-editable metadata, the baseline signature, accepted
finite bounded queries, invalid quotes/calendars/vectors, rejected solver
state, live-value mutations and out-of-domain queries. No checkout data or
research module is needed. A/B use another independent wheel installation for
the full checkout test resources. The existing project `.venv` is never used or
modified. Artifacts and immutable/source bytes are rechecked after validation.

## Receipts and final approval

Preserve complete attempt receipts, command/stdout/stderr logs, dependency wheel
URLs/hashes, Python/platform/tool provenance, build backend logs, archive member
inventories, artifact `SHA256SUMS.txt`, pip reports/check/inspect/freeze, module
origins, consumer results, and applicable selection/JUnit/resource evidence.
GitHub uploads only sanitized `public` receipts, never exports, environments,
private snapshots or entire staging directories. PR retention is 14 days;
manual numerical/release retention is 30 days. A cancelled job may not finish its
receipt trap; absent receipts remain incomplete and cannot pass.

Local preview results belong in the external C06b1 review package and must keep
that label. No full Tier A/B result or real GitHub workflow success is inferred
from static YAML checks or verifier self-tests. C06b2 must use the reviewed
post-merge immutable SHA and retain separate attempts without overwriting them.

C06c requires A/B/C evidence for the reference candidate, reviewed lower-bound
and current-resolver A/C compatibility evidence, actual GitHub scope/aggregate
behavior, resource observations, residual-risk decisions, effective required
checks (or a documented owner hold), and durable retention of exact artifact
bytes and hashes. It also reviews current registry ownership/version availability
and remote tag identity before any separately authorized publication. Suggested
future monorepo tag: `yield-curves/v0.1.0`; this infrastructure never creates it.
Failures do not authorize changes to financial code, assertions, frozen
references, dependency ranges, policies or version identities. Stop the affected
gate and obtain separate corrective scope when needed.
