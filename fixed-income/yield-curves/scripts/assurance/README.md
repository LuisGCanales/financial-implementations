# Assurance scripts

`validate_baseline_curve.py rebuild` calibrates explicit quotes/calendar again.
`validate_baseline_curve.py snapshot --output-root PATH` verifies the current
snapshot and reprices its persisted curve without executing calibration.
Neither mode writes or publishes artifacts. See [CLI workflows](../../docs/cli.md).

`capture_baseline_reference.py` remains the explicit developer tool for capturing
a new numerical reference candidate; it refuses to overwrite existing files.
Historical sequential diagnostics remain in `../experiments/bootstrap/`.
