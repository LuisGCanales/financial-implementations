# Numerical reference candidates

These repository tools support test maintenance and human review. They do not
publish snapshots or perform operational assurance.

From the repository root, after installing `.[dev,plots]`:

```bash
python scripts/tests/capture_baseline_reference.py --help
python scripts/tests/capture_baseline_reference.py --output /tmp/baseline-candidate.json
python scripts/experiments/synthetic/generate_synthetic_reference_data.py --output /tmp/synthetic-candidate.csv
```

Choose a new output path for every run. Both tools require `--output`, reject
both canonical reference paths (including resolved aliases), and refuse existing
destinations. Exclusive file creation also rejects a competing writer. There is
no overwrite or approval flag. Generating either candidate is explicit numerical
work; help and invalid-argument checks do not run it.

Capture reads the frozen 15-quote CSV, uses the projected 2026–2057 calendar and
calls `build_baseline_ftiie_curve` with its default initialization. Rejected
results produce no candidate. The JSON retains the v1 numerical fields: nodes,
one interior sample per segment, forward rates, input hashes and acceptance
checks. Live acceptance binding is intentionally not serialized into this test
format. Environment versions are recorded; byte determinism is limited to the
same inputs and numerical environment, not promised across NumPy/SciPy versions.

The CSV generator retains the existing scenario, truth parameters and dates.
Its existing deterministic serializer writes privately before exclusive candidate
creation. Neither tool changes tests, tolerances or the frozen references.

Review input hashes, environment and numerical differences against
`tests/fixtures/ftiie_baseline_reference_v1.json` or
`data/synthetic/ftiie_ois_quotes_v1.csv`. A maintainer must separately decide any
manual reference update and its revision; candidate generation never approves
it. Fixture/scenario versions are independent of package, baseline-policy and
snapshot-schema versions. Numerical regression is not market truth.
