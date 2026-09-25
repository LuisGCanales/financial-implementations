# Assurance Scripts

This directory contains checks for the current operational baseline.

Historical sequential-bootstrap diagnostics remain under `experiments/bootstrap/` and must not be confused with acceptance of the future cubic baseline.

The current baseline check is `validate_baseline_curve.py`. It validates the
current simultaneous `CUBIC_CONTINUOUS_ZERO` baseline and returns exit code 0
only when `accepted_for_use` is true.
