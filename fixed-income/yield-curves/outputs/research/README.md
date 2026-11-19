# Research Outputs — Curve Construction, Recovery and Sensitivity

This directory organizes **plots, numerical comparisons and diagnostics** from controlled experiments with the MXN F-TIIE OIS term-structure implementation. It is a workspace for **financial-methodology research**, not the mechanism for publishing an accepted operational curve.

The current experiments use **synthetic OIS quotations** and, where long dated, a **projected MXMC calendar**. Their outputs should not be described as observed market data, an official market curve or an independently certified valuation.

## How results are organized

| Output type | Purpose |
|---|---|
| `figures/` | Plots of term structures, interpolation comparisons and sensitivities |
| `tables/` | Machine-readable CSV metrics and saved series used by reports or figures |
| `text/` | Readable diagnostic and result summaries |
| `metadata/` | Experiment configuration, execution details and input/output references |

Within these categories, files are grouped by **research question**. The numeric directory prefixes are preserved as stable filesystem paths and do not define a sequence that a reader must follow.

| Research area | Existing output directory | Main question |
|---|---|---|
| Synthetic reference curve | `01_synthetic_reference/` | What curve and par-rate observations generate the controlled calibration problem? |
| Sequential bootstrap recovery | `02_bootstrap_recovery/` | Can the sequentially constructed curve reprice and recover the synthetic reference? |
| Repricing and structure validation | `03_curve_validation/` | Are calibrated instruments repriced independently, and do the nodes pass method-specific checks? |
| Forward-curve diagnostics | `04_curve_diagnostics/` | What shapes and segment discontinuities arise under log-linear construction? |
| Sequential quote sensitivity | `05_quote_sensitivity/` | How do one-sided and central quote shocks affect nodes? **No retained output section is currently present here.** |
| Interpolation comparison | `06_interpolation_comparison/` | How do alternative representations affect fit, recovery and forward behavior? Retained files cover only the available original comparisons. |
| Global quote sensitivity | `07_global_sensitivity/` | How do shocked quotations propagate through nodes and forward rates under simultaneous calibration? |

These names locate stored outputs in the repository; **they are not a claim that every original result or input is present**. In particular, some full experiments and original metadata exist only in separately archived evidence.

## Relationship to published research exhibits

[Research evidence](../../docs/evidence/index.md) provides a **reader-oriented selection** of the valuation, interpolation and sensitivity findings with public original CSVs, figures and explicit limitations. Its curated exhibits under `evidence/c03/` are **not interchangeable with the full original reports directories**.

[Experiment scripts](../../scripts/README.md) identify which processes recalibrate, generate plots or consume **previously saved numerical data**. For expensive sensitivity experiments, stored matrices allow some visualizations and locality summaries to be generated **without rerunning the financial optimizer**.

Consult the [reproduction contract](../../docs/evidence/reproduce.md) for the verified scope. A successful saved-data replay does **not** imply a full financial reconstruction of every research result.

## Reproduction and file provenance

Research producer scripts usually write their outputs under `outputs/research/` through reporting helpers, with an explicit `reports_root` override in supported workflows. Reuse of the **same financial inputs, date grids, method, and numerical environment** matters when comparing results.

The saved research outputs were moved from an earlier `reports/` location **without changing the file bytes or rerunning their experiments**. Paths embedded in original metadata may still describe that original execution context; they are preserved as provenance, not presented as present-day lookup locations.

Input datasets are documented separately under [`data/`](../../data/README.md). Operational accepted runs, by contrast, are managed through a caller-selected **snapshot output root**, with `current.json` resolving a run archive; they are not selected from research figures or tables.

[Financial methodology](../../docs/methodology.md) · [Evidence overview](../../docs/evidence/index.md) · [Snapshot and publication contract](../../docs/snapshots.md)
