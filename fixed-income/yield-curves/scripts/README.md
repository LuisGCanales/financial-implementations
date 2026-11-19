# Repository Scripts — Usage and Research Navigation

The checkout scripts expose **execution workflows and reproducible financial experiments**. They are distinct from the in-memory Python curve interface. Begin with the intended purpose rather than the chronological order in which a script was developed.

| Need | Directory | What it does |
|---|---|---|
| Build and archive the selected baseline using explicit inputs | [`operational/`](operational/README.md) | Performs calibration and standard acceptance; promotes **only accepted** runs |
| Independently assess an existing or newly rebuilt baseline | [`assurance/`](assurance/README.md) | Rebuilds without publication, or verifies archived nodes **without recalibration** |
| Reproduce the frozen synthetic example | [`demo/`](demo/README.md) | Uses known synthetic quotations and a projected calendar; writes demo snapshots |
| Study calibration and interpolation behavior | `experiments/` | Synthetic inputs, bootstrap, method comparisons, forward curves and sensitivities |
| Capture test reference candidates | [`tests/`](tests/README.md) | Developer-maintained numerical references; not a publishing workflow |

For usage commands, use [CLI workflows](../docs/cli.md); for downstream Python consumption, use the [integration contract](../docs/integration_contract.md). Research scripts are not stable API entry points for valuation consumers.

## Experimental workflow and source

Experiments use project research utilities, notably the **known synthetic reference curve**, the **projected MXMC calendar**, and the frozen quote file `data/synthetic/ftiie_ois_quotes_v1.csv`. They ask distinct questions:

- **Quote repricing:** can the recovered curve reproduce the input par rates?
- **Known-curve recovery:** how closely do discount factors, zero rates and forwards match their generating synthetic curve?
- **Interpolation behavior:** how do alternative curve representations change shapes and between-pillar rates?
- **Sensitivity:** where do perturbations of individual OIS quotations propagate?

The research directories contain a mix of **calculation producers, figure/report generators, and saved-data consumers**. Re-running all scripts is not required to inspect the curated evidence. Some original outputs live outside the current checkout; consult [evidence and reproduction scope](../docs/evidence/reproduce.md) before claiming a complete replay.

### 1. Construct and inspect synthetic reference inputs

| Script (relative to `experiments/synthetic/`) | Purpose | Data and output |
|---|---|---|
| `generate_synthetic_reference_data.py` | Generate a **new synthetic quotation candidate** from the reference curve and projected calendar | Requires `--output`; **does not overwrite** the frozen input dataset |
| `plot_synthetic_reference_data.py` | Illustrate the known zero curve, 28-day forwards and par OIS quotations | Writes figures/tables to `outputs/research/{figures,tables}/01_synthetic_reference/` |

The source scenario is specified in [Synthetic reference data](../data/synthetic/README.md).

### 2. Sequential bootstrap, repricing and curve diagnostics

These are **valid research uses of the implemented sequential bootstrap**, not acceptance results for the selected simultaneous/natural-cubic baseline.

| Script (relative to `experiments/bootstrap/`) | Purpose | Research output |
|---|---|---|
| `bootstrap_synthetic_reference_data.py` | Recover nodal discount factors from synthetic quotes | Tables and text under `02_bootstrap_recovery/` |
| `plot_bootstrap_recovery.py` | Compare recovered discount factors, zero rates and forwards with the known reference | Figures and tables under `02_bootstrap_recovery/` |
| `report_bootstrap_recovery_metrics.py` | Summarize recovery errors globally and by maturity | Tables and text under `02_bootstrap_recovery/` |
| `validate_synthetic_bootstrap.py` | Reconstruct and independently reprice calibration swaps | Tables and text under `03_curve_validation/` |
| `report_curve_diagnostics.py` | Examine forward-curve shape and log-linear segment jumps | Tables and text under `04_curve_diagnostics/` |
| `report_quote_sensitivity.py` | One-sided quote shocks and sequential upstream locality | Outputs under `05_quote_sensitivity/` **when run** |
| `report_central_quote_sensitivity.py` | Central quote shocks and local curvature diagnostics | Outputs under `05_quote_sensitivity/` **when run** |

Output paths in this table are relative to `outputs/research/`, with `figures/`, `tables/`, or `text/` subfolders depending on the script. The `05_quote_sensitivity/` research-output section is **not currently preserved** in that directory; curated sensitivity exhibits are linked in [Risk evidence](../docs/evidence/risk.md).

### 3. Compare interpolation choices

| Script (relative to `experiments/interpolation/`) | Financial comparison | Output behavior |
|---|---|---|
| `compare_interpolation_methods.py` | Two **sequentially calibrated** interpolation methods | Console comparison |
| `compare_interpolation_methods_by_horizon.py` | Two sequential methods evaluated across maturity horizons | Console comparison |
| `plot_interpolation_method_comparison.py` | Dense visual comparison of two sequential methods | Saves `two_methods` figures/tables under `06_interpolation_comparison/` |
| `compare_three_interpolation_methods.py` | Three interpolations under **simultaneous nodal calibration** | Generates comparison tables/diagnostics and metadata when executed |
| `plot_three_interpolation_methods.py` | Dense recovery and forward-shape comparison for the three simultaneous methods | Produces plots and data when executed |

The **calibration engine differs** between the two-method sequential and three-method simultaneous studies. Their results must not be mixed as if only interpolation had changed. The saved curated comparison can be inspected in [Methodology evidence](../docs/evidence/methodology.md); some original three-method files are not retained under the older research-output directory.

The script names refer to their **specific implemented experiment design**, not a constraint on the set of methods supported by the underlying Python curve library.

### 4. Quote-sensitivity propagation and locality

| Script (relative to `experiments/sensitivity/`) | Purpose | Dependencies |
|---|---|---|
| `report_global_sensitivity.py` | Recalibrate under symmetric **±1 bp quote shocks** and produce global sensitivity results for three methods | **Expensive producer**; writes section `07_global_sensitivity/` data, plots and metadata |
| `plot_global_forward_sensitivity_heatmaps.py` | Plot signed forward-rate response matrices | **Saved-data consumer** of section 07 CSVs; no curve recalibration |
| `report_forward_sensitivity_locality.py` | Summarize where and how strongly shocks propagate | **Saved-data consumer** of section 07 CSVs; no curve recalibration |

The heatmap and locality tools require the persisted `global_forward_sensitivity_dense.csv` and `global_node_sensitivity_long.csv` datasets. Generating these reports from saved data should not be described as re-executing the underlying financial calibration.

[Risk analysis](../docs/evidence/risk.md) · [Saved-data replay requirements](../docs/evidence/reproduce.md)

## Execution and evidence boundaries

The scripts are **checkout workflows**, not a generic installed command-line distribution or an alternative to the consumer API.

An experiment can depend on synthetic truth and research-only utilities; **the operational baseline and its consumers must not**. Snapshot publication, independent acceptance, stored-data replay and full research recomputation are different activities.

Generated experiment files under `outputs/research/` and curated files under `evidence/c03/` are not interchangeable. The [evidence index](../docs/evidence/index.md) and [reproduction contract](../docs/evidence/reproduce.md) identify which results and dependencies are actually available.
