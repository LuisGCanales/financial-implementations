# Script Navigation

This directory separates future operational workflows from historical development research.

- **Use `operational/`** when consuming the project baseline.
- **Use `assurance/`** when validating the current operational baseline.
- **Use `experiments/`** when reproducing development research or historical diagnostics.

The current historical scripts are intentionally placed under `experiments/`.

## Experiments

### `experiments/synthetic`

| Script | Purpose | Inputs | Outputs | Depends on | Cost |
|---|---|---|---|---|---|
| `generate_synthetic_reference_data.py` | Generate the frozen synthetic F-TIIE OIS quote set. | Projected MXMC calendar and the synthetic known-truth model. | Writes `data/synthetic/ftiie_ois_quotes_v1.csv` when executed. | `yield_curves.calendars`, `schedules`, `synthetic`. | MEDIUM |
| `plot_synthetic_reference_data.py` | Plot the known-truth zero/forward curves and synthetic par quotes. | Existing synthetic quote CSV and known-truth model. | Writes figures and tables under `reports/{figures,tables}/01_synthetic_reference/`. | `yield_curves.synthetic`, `reporting`. | LOW |

### `experiments/bootstrap`

These scripts use the historical sequential bootstrap engine. Their validation and diagnostics are development evidence; they are **not acceptance of the current simultaneous cubic baseline**.

| Script | Purpose | Inputs | Outputs | Depends on | Cost |
|---|---|---|---|---|---|
| `bootstrap_synthetic_reference_data.py` | Bootstrap synthetic quotes and report nodal recovery. | `data/synthetic/ftiie_ois_quotes_v1.csv`. | Writes `reports/{tables,text}/02_bootstrap_recovery/` when executed; corresponding historical outputs are currently present. | `yield_curves.bootstrap`, `calendars`, `synthetic`, `reporting`. | MEDIUM |
| `plot_bootstrap_recovery.py` | Plot dense recovery of discount factors, zero rates and forwards. | Synthetic quote CSV and known-truth model. | Writes figures/tables under `reports/{figures,tables}/02_bootstrap_recovery/`. | `yield_curves.bootstrap`, `synthetic`, `reporting`. | MEDIUM |
| `report_bootstrap_recovery_metrics.py` | Calculate global and maturity-horizon recovery metrics. | Synthetic quote CSV and known-truth model. | Writes tables/text under `reports/{tables,text}/02_bootstrap_recovery/`. | `yield_curves.bootstrap`, `recovery`, `synthetic`, `reporting`. | MEDIUM |
| `validate_synthetic_bootstrap.py` | Validate the sequential bootstrap and independently reprice calibration instruments. | Synthetic quote CSV and projected calendar. | Writes tables/text under `reports/{tables,text}/03_curve_validation/`. | `yield_curves.bootstrap`, `validation`, `reporting`. | MEDIUM |
| `report_curve_diagnostics.py` | Diagnose forward-curve shape and log-linear segment jumps. | Synthetic quote CSV and projected calendar. | Writes tables/text under `reports/{tables,text}/04_curve_diagnostics/`. | `yield_curves.bootstrap`, `diagnostics`, `reporting`. | MEDIUM |
| `report_quote_sensitivity.py` | Measure one-sided quote shocks and sequential upstream invariance. | Synthetic quote CSV and projected calendar. | Writes outputs under `reports/{tables,text}/05_quote_sensitivity/` when executed; this section is currently absent from the repository. | `yield_curves.sensitivity`, `reporting`. | HIGH |
| `report_central_quote_sensitivity.py` | Measure symmetric quote sensitivity and local curvature for the sequential engine. | Synthetic quote CSV and projected calendar. | Writes outputs under `reports/{tables,text}/05_quote_sensitivity/` when executed; this section is currently absent from the repository. | `yield_curves.sensitivity`, `reporting`. | HIGH |

### `experiments/interpolation`

This directory preserves historical comparisons of two and three interpolation methods. The `three` names are historical and are deliberately not generalized in this phase.

| Script | Purpose | Inputs | Outputs | Depends on | Cost |
|---|---|---|---|---|---|
| `compare_interpolation_methods.py` | Print global recovery/repricing comparison for two sequential methods. | Synthetic quote CSV and projected calendar. | Console output only. | `yield_curves.bootstrap`, `validation`, `recovery`. | MEDIUM |
| `compare_interpolation_methods_by_horizon.py` | Print recovery comparison by maturity horizon for two sequential methods. | Synthetic quote CSV and projected calendar. | Console output only. | `yield_curves.bootstrap`, `recovery`. | MEDIUM |
| `plot_interpolation_method_comparison.py` | Persist dense visual comparison of two sequential methods. | Synthetic quote CSV, projected calendar and known truth. | Writes the currently present `two_methods` figures/tables under `reports/06_interpolation_comparison/`. | `yield_curves.bootstrap`, `synthetic`, `reporting`. | MEDIUM |
| `compare_three_interpolation_methods.py` | Compare three methods with simultaneous nodal calibration. | Synthetic quote CSV, projected calendar and known truth. | Writes `three_method*`, diagnostics and metadata when executed; those outputs are currently absent. | `yield_curves.calibration`, `recovery`, `reporting`. | HIGH |
| `plot_three_interpolation_methods.py` | Plot dense recovery for three methods, including cubic instantaneous forward. | Synthetic quote CSV, projected calendar and known truth. | Writes `three_methods*` figures/tables when executed; those outputs are currently absent. | `yield_curves.calibration`, `synthetic`, `reporting`. | HIGH |

### `experiments/sensitivity`

| Script | Purpose | Inputs | Outputs | Depends on | Cost |
|---|---|---|---|---|---|
| `report_global_sensitivity.py` | Run and persist global quote-sensitivity comparisons for three methods. | Synthetic quote CSV, projected calendar, symmetric +/- 1 bp shocks. | Writes tables, figures, text and metadata under `reports/07_global_sensitivity/`; existing outputs are consumed below. | `yield_curves.global_sensitivity`, `reporting`. | HIGH |
| `plot_global_forward_sensitivity_heatmaps.py` | Plot forward-sensitivity propagation using persisted results. | Existing `global_forward_sensitivity_dense.csv` and `global_node_sensitivity_long.csv` from section 07. | Writes heatmaps and scale diagnostics under section 07. | Persisted section 07 CSVs; `yield_curves.reporting`. | MEDIUM |
| `report_forward_sensitivity_locality.py` | Derive forward-sensitivity locality metrics from persisted results. | The same two section 07 CSVs. | Writes locality tables, figures, text and metadata under section 07. | Persisted section 07 CSVs; `yield_curves.global_sensitivity`, `reporting`. | MEDIUM |

The global sensitivity producer is expensive. The heatmap and locality scripts consume persisted CSVs and do not recalibrate curves.

## Operational and assurance entrypoints

The operational Python contract is:

```python
from yield_curves.baseline import build_baseline_ftiie_curve
```

The operational script is `operational/build_baseline_curve.py` and writes
`outputs/baseline/`. The assurance script is
`assurance/validate_baseline_curve.py`; it validates the current simultaneous
`CUBIC_CONTINUOUS_ZERO` baseline.

No external consumer should depend on experiment scripts or historical
reports.
