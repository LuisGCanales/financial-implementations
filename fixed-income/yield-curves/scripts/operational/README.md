# Operational Scripts

This directory contains stable workflows that build and export the selected project baseline.

The current baseline is simultaneous nodal calibration with `CUBIC_CONTINUOUS_ZERO`.

No external consumer should depend on scripts under `experiments/`.

The primary Python contract is:

```python
from yield_curves.baseline import build_baseline_ftiie_curve
```

The operational demonstration script is `build_baseline_curve.py`. It writes
the current snapshot to `outputs/baseline/` without modifying `reports/`.
