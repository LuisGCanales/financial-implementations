# Claims C07–C14: methodology and risk

[Evidence index](index.md) · [Methodology](methodology.md) · [Risk](risk.md) · [Machine-readable manifest](../../evidence/c03/methodology-risk-manifest.json) · [Unified claims](claims.md) · [Reproduce](reproduce.md) · [Unified index](../../evidence/c03/index.json)

Original C04a claim identities are preserved below. All claims concern previously validated C03 evidence from synthetic `FTIIE_KNOWN_TRUTH_V1`, projected MXMC 2026–2057, reference date 2026-09-18 and same-curve projection/discounting. C04c supplies authored interpretation and static curation, with no new financial results.

**Historical pre-PR review status: `C04C_READY_FOR_PR_REVIEW`.** H03/H04 are paired, human-approved presentation derivatives from unchanged validated financial matrices. Their footers are outside the data; the complete 30Y response row is visible. Only the out-of-domain 30Y payment-pillar marker is omitted. Robust clipping is **1.5023474%** of cubic cells; full-range clipping is **0%**. M04/G06/H02/L02 remain withheld for absolute local paths, with original hashes and expressly authored provenance summaries in the manifest. Their original files are not replaced by those summaries.

Original financial source commit for every record: **`bee31fd0883660f171ebe84817b98641239eae5b`**. Historical curation started from **`39f24aff2e2c5e13d2eb53ab43d4fee53cc18dae`** on branch `c04c-methodology-risk-evidence`; the base commit is not the financial execution identity. Exact original timestamps, source-script hashes, command-receipt hashes and separate curation time are in the manifest.

Each `C03…/…` evidence identifier below names a file relative to the retained external checkpoint archive. It is an archival identity, **not a public download or an inaccessible local hyperlink**. Public exhibit and source-code links resolve relative to this repository; original source hashes bind scripts to the historical financial source commit. The linked heatmap script now includes the C04c-F01 presentation-only revision; its rendering identity is separate from its original script hash.

For H03/H04, the **Original SHA-256** columns below identify historical C03b2a images retained externally; the public links resolve to the approved derivatives in this table. Classification: `PRESENTATION_DERIVATIVE_FROM_VALIDATED_DATA`. Both use unchanged saved matrices and source-data dependencies; observable public figures do not supply full research reproducibility. Rendering used project Python 3.11.15, Matplotlib 3.11.2, NumPy 2.4.6, SciPy 1.17.1 and Pillow 12.3.0. The rendering script SHA-256 is `3c3844dd9f133f88199fd4de1c2d48ede9de499ee1d0dabbcbc612b496a6c4e8`, an uncommitted C04c-F01 working-tree revision based on `39f24aff2e2c5e13d2eb53ab43d4fee53cc18dae`. Rendering timestamps, historical timestamps and integration/curation timestamps are separately recorded in the manifest.

| Published derivative | Public bytes | Public PNG SHA-256 |
| --- | ---: | --- |
| [H03 robust common scale](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png) | 151971 | `30c92c26b5ddc2774c0d8c700f3204636f09461f471be7c9f004d6fef875ed3a` |
| [H04 full common scale](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png) | 145752 | `d83abfd9abb197eba45c5dad8d102a2c14ff4fed063ea3464da3abab850c1a04` |

[C06: fit versus known-truth recovery](claims-valuation.md#c06) and [its original discussion](valuation.md#h-fit-versus-known-truth-recovery) remain unchanged. C01–C06 continue to use the existing C04b manifest.

## C07

**Supported wording:** Core-v1 uses the same curve for projection and discounting; strict sequential freezing is used for local log-linear construction, while the cubic baseline solves nodes simultaneously.

**Claim type:** methodology assumption. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Explains which valuation problem is actually implemented.

**Methodology:** Sequential Brent terminal-node solves vs simultaneous nodal least squares; natural cubic continuous-zero representation.

**Units:** nodal DF; continuous zero annual decimal

**Limitations:** Project model assumption, not a statement of institutional MXN discounting architecture.

**Original source artifact IDs:** B04, M04, S07.

**Available public artifacts:** B04.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| B04: `C03b2b/reports/B/bootstrap_synthetic_reference_data/tables/02_bootstrap_recovery/bootstrap_node_recovery.csv` | [B04](../../evidence/c03/bootstrap/bootstrap_node_recovery.csv) | `6018fd6b7ee525cd0400f7b472e52c3712a4407393e977ba6116c026b0761414` |
| M04: `C03b2b/reports/C/compare_three_interpolation_methods/metadata/06_interpolation_comparison/experiment_metadata.json` | External only; no public download | `4cbd00b1237b0d1b9b605d7b2dcd2ff4f4717e9620d7e037b9c781b77202e1ed` |
| S07: `C03b1/operational_snapshot/runs/ab8b26ab993140dca7dcbd7491c3a8c0/metadata.json` | External only; no public download | `7c7a14588c276ec6156f5559f3451d2efb3cecac428e3e4aaa78868c4ab9b945` |
| audit: `C03c/coverage-matrix.json` | External only; no public download | `ce4b84c772fc187e3107b211bfb7d0ed6249f2794a5f23513328c9b4fdca10ca` |

**Original scripts and workflows:**

- [scripts/experiments/bootstrap/bootstrap_synthetic_reference_data.py](../../scripts/experiments/bootstrap/bootstrap_synthetic_reference_data.py); workflow/original audit role `bootstrap_synthetic_reference_data`; SHA-256 `17aad20a61c7de704e6b36d0fb175d8d0ca52ea75eefbb322dc6d7e624a5f9e2`.
- [scripts/experiments/interpolation/compare_three_interpolation_methods.py](../../scripts/experiments/interpolation/compare_three_interpolation_methods.py); workflow/original audit role `compare_three_interpolation_methods`; SHA-256 `04544e59a71fcafceecd62b470fc93ea419124c790ac32ef60d4edd5c606423b`.
- [scripts/operational/build_baseline_curve.py](../../scripts/operational/build_baseline_curve.py); workflow/original audit role `snapshot-build`; SHA-256 `b34d4e702ad496fa11b2494322eb7eb5dc21b7297f3c71adb78a74708422834b`.
- `C03c/metadata/build_delivery.py` (external audit source); workflow/original audit role `original audit program; not a financial producer`; SHA-256 `e54ccc032bd1865f1917a8b00523f0f21cea08e485222030915dc519d9cad7d7`.

**External evidence dependencies:** `C03b1/operational_snapshot/runs/ab8b26ab993140dca7dcbd7491c3a8c0/metadata.json`; `C03b2b/reports/C/compare_three_interpolation_methods/metadata/06_interpolation_comparison/experiment_metadata.json`; `C03c/coverage-matrix.json`.

## C08

**Supported wording:** In the shared simultaneous three-method study, all three calibrations succeed; saved 28D-forward recovery RMSE is 3.811009931078169 bp for log-linear DF and 0.24931760566157052 bp for cubic continuous zero.

**Claim type:** observed result. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Shows measurable methodology tradeoffs with controlled engine and inputs.

**Methodology:** Compare method rows within M02 only; M03 supplies all horizons and all methods. Known truth is introduced after calibration.

**Units:** repricing/zero/forward bp; DF absolute

**Limitations:** Single smooth synthetic truth; does not establish universal superiority or observed-market suitability. Zero-plot and metrics grids are different.

**Original source artifact IDs:** M01, M02, M03, M04, M05.

**Available public artifacts:** M01, M02, M03, M05.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| M01: `C03b2b/reports/C/compare_three_interpolation_methods/tables/06_interpolation_comparison/simultaneous_calibration_diagnostics.csv` | [M01](../../evidence/c03/methodology/simultaneous_calibration_diagnostics.csv) | `ea8873afc30ec0412eb09c8865d22d9e499407372472ad8fd833754796a03a62` |
| M02: `C03b2b/reports/C/compare_three_interpolation_methods/tables/06_interpolation_comparison/three_method_global_recovery.csv` | [M02](../../evidence/c03/methodology/three_method_global_recovery.csv) | `5a948bca410d6653dac8ef4fd7d54673ecf2f756b61b85d385e5bc6e9ab1e8cb` |
| M03: `C03b2b/reports/C/compare_three_interpolation_methods/tables/06_interpolation_comparison/three_method_recovery_by_horizon.csv` | [M03](../../evidence/c03/methodology/three_method_recovery_by_horizon.csv) | `420e1afa2bd0202d5a2353e833d73465cf8abd3995c2d763659e7c9990329a58` |
| M04: `C03b2b/reports/C/compare_three_interpolation_methods/metadata/06_interpolation_comparison/experiment_metadata.json` | External only; no public download | `4cbd00b1237b0d1b9b605d7b2dcd2ff4f4717e9620d7e037b9c781b77202e1ed` |
| M05: `C03b2b/reports/C/plot_three_interpolation_methods/figures/06_interpolation_comparison/forward_28d_recovery_three_methods.png` | [M05](../../evidence/c03/methodology/forward_28d_recovery_three_methods.png) | `50b2b01fa4e45832d731a9f0eba120cdd22a7a2627cbdf9e495fe1652a13b195` |

**Original scripts and workflows:**

- [scripts/experiments/interpolation/compare_three_interpolation_methods.py](../../scripts/experiments/interpolation/compare_three_interpolation_methods.py); workflow/original audit role `compare_three_interpolation_methods`; SHA-256 `04544e59a71fcafceecd62b470fc93ea419124c790ac32ef60d4edd5c606423b`.
- [scripts/experiments/interpolation/plot_three_interpolation_methods.py](../../scripts/experiments/interpolation/plot_three_interpolation_methods.py); workflow/original audit role `plot_three_interpolation_methods`; SHA-256 `ac6d99ef642688756f972fc6f66792176d3e6ced76275f96b41c8dfb32425683`.

**External evidence dependencies:** `C03b2b/metadata/cross-workflow-consistency.json`; `C03b2b/reports/C/compare_three_interpolation_methods/metadata/06_interpolation_comparison/experiment_metadata.json`; `C03b2b/reports/C/plot_three_interpolation_methods/tables/06_interpolation_comparison/forward_28d_recovery_three_methods_dense.csv`.

## C09

**Supported wording:** Section 05 one-sided and central workflows persist finite 15×15 node matrices with exact upstream zeros and matching own-node summary diagonals.

**Claim type:** observed result. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Provides inspectable local quote-to-node risk responses.

**Methodology:** Sequential LOG_LINEAR_DF; +1 bp and ±1 bp quote shocks. C03 structural/internal financial tests passed.

**Units:** matrix rows=shocked quotes; columns=responding nodes; bp/bp

**Limitations:** No tracked historical section 05 baseline; no historical equality claimed; do not transfer exact-zero behavior to the simultaneous global engine.

**Original source artifact IDs:** Q01, Q02, Q03, Q04, Q05.

**Available public artifacts:** Q01, Q02, Q03, Q04, Q05.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| Q01: `C03b2b/reports/B/report_quote_sensitivity/tables/05_quote_sensitivity/one_sided_quote_sensitivity_summary.csv` | [Q01](../../evidence/c03/section05/one_sided_quote_sensitivity_summary.csv) | `57f1a55ecd7d62c83d428338e8a59b79b1efd4d6a1b1f0b802a1ef550565f7bd` |
| Q02: `C03b2b/reports/B/report_quote_sensitivity/tables/05_quote_sensitivity/one_sided_zero_sensitivity_matrix.csv` | [Q02](../../evidence/c03/section05/one_sided_zero_sensitivity_matrix.csv) | `574a8c6cba4851c53437a3c1af16b661be5865f5909cdfba33521dd9c470f2b4` |
| Q03: `C03b2b/reports/B/report_central_quote_sensitivity/tables/05_quote_sensitivity/central_quote_sensitivity_summary.csv` | [Q03](../../evidence/c03/section05/central_quote_sensitivity_summary.csv) | `ff2ad6dfe8424896d1fc5ef9c4e78ce98c1a04f9d9170e3326d9c1439c5bb390` |
| Q04: `C03b2b/reports/B/report_central_quote_sensitivity/tables/05_quote_sensitivity/central_zero_sensitivity_matrix.csv` | [Q04](../../evidence/c03/section05/central_zero_sensitivity_matrix.csv) | `d4d7a732e21a4a06e70a254ba6b096a356edf92b5a4f67cd0e819c5e0112da1e` |
| Q05: `C03b2b/reports/B/report_central_quote_sensitivity/tables/05_quote_sensitivity/own_node_local_curvature.csv` | [Q05](../../evidence/c03/section05/own_node_local_curvature.csv) | `6accab217ab1c2215cd48fdf6b1b25f55c89adb4e4ee9694c1976afed79d0ca5` |
| audit: `C03b2b/metadata/quote-sensitivity-validation.json` | External only; no public download | `33cced8cbf12d98bfd7bfa149ba3a15579697ac3b4201d143571c451ddb60596` |

**Original scripts and workflows:**

- [scripts/experiments/bootstrap/report_quote_sensitivity.py](../../scripts/experiments/bootstrap/report_quote_sensitivity.py); workflow/original audit role `report_quote_sensitivity`; SHA-256 `8535699fc12dc5a7e9d55edcf9e17e381173eb0561933fdcc7521b48a409533b`.
- [scripts/experiments/bootstrap/report_central_quote_sensitivity.py](../../scripts/experiments/bootstrap/report_central_quote_sensitivity.py); workflow/original audit role `report_central_quote_sensitivity`; SHA-256 `630afb2aafbe4090d637b92dfd1895acd0e6c594d3350c44ae9588cfe3077aff`.
- `C03b2b/validate_evidence.py` (external audit source); workflow/original audit role `original audit program; not a financial producer`; SHA-256 `47338a6c77dab284d37f3fecc64c10d282a0f9448281a616cfb2ca75d887c0a6`.

**External evidence dependencies:** `C03b2b/metadata/quote-sensitivity-validation.json`.

## C10

**Supported wording:** The section 05 30Y one-sided own-node zero change is 2.497681564725407 bp for +1 bp; central sensitivity is 2.490478975129551 bp/bp and local curvature is 0.014405179191712136 bp/bp².

**Claim type:** observed result. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Demonstrates asymmetric local response and finite-difference curvature.

**Methodology:** D+ = (Z+−Z0)/h; Dc=(Z+−Z−)/(2h); C=(Z+−2Z0+Z−)/h², where Z is node zero in bp and h=1 quote bp.

**Units:** bp change; bp/bp; bp/bp²

**Limitations:** Different estimators, not contradictory results; curvature is finite-bump node-rate response, not portfolio gamma or an analytic derivative. Floating arithmetic residuals are disclosed in original checker.

**Original source artifact IDs:** Q01, Q03, Q05.

**Available public artifacts:** Q01, Q03, Q05.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| Q01: `C03b2b/reports/B/report_quote_sensitivity/tables/05_quote_sensitivity/one_sided_quote_sensitivity_summary.csv` | [Q01](../../evidence/c03/section05/one_sided_quote_sensitivity_summary.csv) | `57f1a55ecd7d62c83d428338e8a59b79b1efd4d6a1b1f0b802a1ef550565f7bd` |
| Q03: `C03b2b/reports/B/report_central_quote_sensitivity/tables/05_quote_sensitivity/central_quote_sensitivity_summary.csv` | [Q03](../../evidence/c03/section05/central_quote_sensitivity_summary.csv) | `ff2ad6dfe8424896d1fc5ef9c4e78ce98c1a04f9d9170e3326d9c1439c5bb390` |
| Q05: `C03b2b/reports/B/report_central_quote_sensitivity/tables/05_quote_sensitivity/own_node_local_curvature.csv` | [Q05](../../evidence/c03/section05/own_node_local_curvature.csv) | `6accab217ab1c2215cd48fdf6b1b25f55c89adb4e4ee9694c1976afed79d0ca5` |

**Original scripts and workflows:**

- [scripts/experiments/bootstrap/report_quote_sensitivity.py](../../scripts/experiments/bootstrap/report_quote_sensitivity.py); workflow/original audit role `report_quote_sensitivity`; SHA-256 `8535699fc12dc5a7e9d55edcf9e17e381173eb0561933fdcc7521b48a409533b`.
- [scripts/experiments/bootstrap/report_central_quote_sensitivity.py](../../scripts/experiments/bootstrap/report_central_quote_sensitivity.py); workflow/original audit role `report_central_quote_sensitivity`; SHA-256 `630afb2aafbe4090d637b92dfd1895acd0e6c594d3350c44ae9588cfe3077aff`.

**External evidence dependencies:** None beyond the original execution/provenance records retained externally..

## C11

**Supported wording:** The global study covers 3 base plus 90 shocked simultaneous calibrations, all successful within the existing 0.01 bp repricing policy; G01 retains 45 method/shock rows.

**Claim type:** observed result. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Establishes calibration credibility before interpreting propagated risk.

**Methodology:** 3 interpolation methods × 15 one-factor ±1 bp quote shocks; 28D forwards sampled every 7 days.

**Units:** repricing bp; response bp/bp; curvature bp/bp²

**Limitations:** Not a correlated stress, portfolio P&L, hedging or monetary DV01 study.

**Original source artifact IDs:** G01, G02, G06.

**Available public artifacts:** G01, G02.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| G01: `C03b2a/full-global-root/tables/07_global_sensitivity/global_sensitivity_summary.csv` | [G01](../../evidence/c03/global/global_sensitivity_summary.csv) | `42e571ff3c58cf3a87cbeac3573818dab1329136722d38bc88ea53b899416bb9` |
| G02: `C03b2a/full-global-root/tables/07_global_sensitivity/global_calibration_diagnostics.csv` | [G02](../../evidence/c03/global/global_calibration_diagnostics.csv) | `a30987b133c522a13eb73dfaf04851db4fc8d4f0b722816381cd824d00fc7f01` |
| G06: `C03b2a/full-global-root/metadata/07_global_sensitivity/experiment_metadata.json` | External only; no public download | `58d40ffe14c4eabbfc8286f2b8fd3797b851a3aa0820201ed7d9310f17cb3614` |
| audit: `C03b2a/metadata/producer-structure-validation.json` | External only; no public download | `8496ee1962d660eed13ac0bc42c3e96bbcdbbd8935534e182a75bfb4d6273ceb` |

**Original scripts and workflows:**

- [scripts/experiments/sensitivity/report_global_sensitivity.py](../../scripts/experiments/sensitivity/report_global_sensitivity.py); workflow/original audit role `global`; SHA-256 `c14a7222a61082783edc7585e04ee071088fe777ef27e53f221086e8e7f984fe`.
- [scripts/experiments/sensitivity/report_global_sensitivity.py](../../scripts/experiments/sensitivity/report_global_sensitivity.py); workflow/original audit role `financial workflow`; SHA-256 `c14a7222a61082783edc7585e04ee071088fe777ef27e53f221086e8e7f984fe`.

**External evidence dependencies:** `C03b2a/full-global-root/metadata/07_global_sensitivity/experiment_metadata.json`; `C03b2a/metadata/producer-structure-validation.json`.

## C12

**Supported wording:** Cubic forward responses spread across the curve; a small-looking nodal off-diagonal heatmap cell does not prove absence of forward propagation.

**Claim type:** interpretation. **Evidence strength:** `STRONG_SCENARIO_SPECIFIC_INTERPRETATION`.

**Financial interpretation:** Links interpolation choice to hedge localization and model-risk questions.

**Methodology:** Read signed matrices and forward sensitivity together; distinguish responding nodes from off-node forward starts.

**Units:** bp/bp

**Limitations:** Node heatmap sequential palette suppresses sign/small magnitude; future narrative may omit that figure after review. No quantified hedging effectiveness claimed.

**Presentation provenance:** H03/H04 are approved presentation derivatives with unchanged financial matrices. Robust and full scales remain paired; clipping is 1.5023474% and 0%, respectively. The out-of-domain 30Y pillar marker is omitted; the complete 30Y response row remains. Historical image and rendering provenance are separately bound in the manifest.

**Original source artifact IDs:** G01, G03, G04, G05, G07, H03, H04.

**Available public artifacts:** G01, G03, G04, G05, H03, H04.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| G01: `C03b2a/full-global-root/tables/07_global_sensitivity/global_sensitivity_summary.csv` | [G01](../../evidence/c03/global/global_sensitivity_summary.csv) | `42e571ff3c58cf3a87cbeac3573818dab1329136722d38bc88ea53b899416bb9` |
| G03: `C03b2a/full-global-root/tables/07_global_sensitivity/node_zero_sensitivity_matrix_log_linear_df.csv` | [G03](../../evidence/c03/global/node_zero_sensitivity_matrix_log_linear_df.csv) | `bef56ddcb4695f551c22a8018e51e377df868e827422ea1f9f160570000bfb64` |
| G04: `C03b2a/full-global-root/tables/07_global_sensitivity/node_zero_sensitivity_matrix_linear_continuous_zero.csv` | [G04](../../evidence/c03/global/node_zero_sensitivity_matrix_linear_continuous_zero.csv) | `6071b4c13b315f30850c2fe295640cd7fad927a68c262c87891608096212d28b` |
| G05: `C03b2a/full-global-root/tables/07_global_sensitivity/node_zero_sensitivity_matrix_cubic_continuous_zero.csv` | [G05](../../evidence/c03/global/node_zero_sensitivity_matrix_cubic_continuous_zero.csv) | `a8dc5e5da4aa9db2913ddbd70874431c2750831d3d33ad0be7c34d45b81606fb` |
| G07: `C03b2a/full-global-root/figures/07_global_sensitivity/node_zero_sensitivity_heatmap_cubic_continuous_zero.png` | EXCLUDED; original retained externally; not public support | `24ac8192ff0f2847985223b238762635b027c5a44e377f221c29ceb3867eb5cc` |
| H03: `C03b2a/full-global-root/figures/07_global_sensitivity/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png` | [H03](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png) | `8d406ed6f7390f7f09d00bc8448afaecafd54b2ee71c5361672f2f8c0874adc4` |
| H04: `C03b2a/full-global-root/figures/07_global_sensitivity/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png` | [H04](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png) | `4f202724ca1bcf9615cadaa22373604cc5e7a761fcfbb89f38f4be23f1038428` |

**Original scripts and workflows:**

- [scripts/experiments/sensitivity/report_global_sensitivity.py](../../scripts/experiments/sensitivity/report_global_sensitivity.py); workflow/original audit role `global`; SHA-256 `c14a7222a61082783edc7585e04ee071088fe777ef27e53f221086e8e7f984fe`.
- [scripts/experiments/sensitivity/plot_global_forward_sensitivity_heatmaps.py](../../scripts/experiments/sensitivity/plot_global_forward_sensitivity_heatmaps.py); workflow/original audit role `heatmaps`; SHA-256 `c5b62462070a2cd1ac7ba1d51553d6352bbc55b75869fa21d4201d2cc67ce754`.

**External evidence dependencies:** `C03b2a/full-global-root/figures/07_global_sensitivity/node_zero_sensitivity_heatmap_cubic_continuous_zero.png`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_forward_sensitivity_dense.csv`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_node_sensitivity_long.csv`.

## C13

**Supported wording:** Robust heatmaps use a common pooled 99.5th-percentile cap of ±11.33194135019177 bp/bp; full scale is ±20.04398642012309 bp/bp. Cubic clipped fraction is 0.015023474178403756; full plots intentionally clip none.

**Claim type:** observed result. **Evidence strength:** `STRONG_WITHIN_DECLARED_SCOPE`.

**Financial interpretation:** Prevents color saturation from understating tail amplification.

**Methodology:** Scales pooled across all methods; robust scale intentionally saturates tails.

**Units:** bp/bp; clipped fraction 0–1 (1.5023474% cubic)

**Limitations:** Selected figures show cubic only; all methods appear in H01 and G01. Compare colors only under the stated common scale, never robust vs full without accounting for caps.

**Presentation provenance:** H03/H04 are approved presentation derivatives with unchanged financial matrices. Robust and full scales remain paired; clipping is 1.5023474% and 0%, respectively. The out-of-domain 30Y pillar marker is omitted; the complete 30Y response row remains. Historical image and rendering provenance are separately bound in the manifest.

**Original source artifact IDs:** H01, H02, H03, H04.

**Available public artifacts:** H01, H03, H04.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| H01: `C03b2a/full-global-root/tables/07_global_sensitivity/forward_sensitivity_heatmap_scale_diagnostics.csv` | [H01](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_scale_diagnostics.csv) | `39315d80286b50ced878b07f24b44c97213a285c4b2f72d7a3d94424dbc2a307` |
| H02: `C03b2a/full-global-root/metadata/07_global_sensitivity/forward_sensitivity_heatmap_metadata.json` | External only; no public download | `5ce01f5f845c3ff5b31c3e68ca8614687385e41042e04cc9c0f97f73a4f5b7d5` |
| H03: `C03b2a/full-global-root/figures/07_global_sensitivity/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png` | [H03](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png) | `8d406ed6f7390f7f09d00bc8448afaecafd54b2ee71c5361672f2f8c0874adc4` |
| H04: `C03b2a/full-global-root/figures/07_global_sensitivity/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png` | [H04](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png) | `4f202724ca1bcf9615cadaa22373604cc5e7a761fcfbb89f38f4be23f1038428` |

**Original scripts and workflows:**

- [scripts/experiments/sensitivity/plot_global_forward_sensitivity_heatmaps.py](../../scripts/experiments/sensitivity/plot_global_forward_sensitivity_heatmaps.py); workflow/original audit role `heatmaps`; SHA-256 `c5b62462070a2cd1ac7ba1d51553d6352bbc55b75869fa21d4201d2cc67ce754`.

**External evidence dependencies:** `C03b2a/full-global-root/metadata/07_global_sensitivity/forward_sensitivity_heatmap_metadata.json`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_forward_sensitivity_dense.csv`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_node_sensitivity_long.csv`.

## C14

**Supported wording:** Locality depends on tenor and metric: cubic ±2Y sensitivity mass at the 30Y shock is 0.29034212262038983, and the selected all-method plot shows cubic above both challengers there.

**Claim type:** interpretation. **Evidence strength:** `STRONG_SCENARIO_SPECIFIC_INTERPRETATION`.

**Financial interpretation:** Avoids overselling a universal method ranking.

**Methodology:** w_j=|central forward sensitivity_j|/sum|sensitivity|; mass sums weights with |t_j−T_shock|≤2 ACT/360 years; RMS uses saved weighted distance.

**Units:** fractions in CSV; percentages in figure; years for distances

**Limitations:** Absolute weights discard response sign. These are sampled curve-response metrics, not probabilities, portfolio risk or a guarantee that cubic is always less local. Finite domain affects boundary shocks.

**Original source artifact IDs:** L01, L02, L03.

**Available public artifacts:** L01, L03.

| Original evidence identity | Public availability | Original SHA-256 |
| --- | --- | --- |
| L01: `C03b2a/full-global-root/tables/07_global_sensitivity/forward_sensitivity_locality.csv` | [L01](../../evidence/c03/locality/forward_sensitivity_locality.csv) | `de59820c13e5cbcf21d36e4ad86184eb43709192c8a7c2a14c466a18918db340` |
| L02: `C03b2a/full-global-root/metadata/07_global_sensitivity/forward_sensitivity_locality_metadata.json` | External only; no public download | `036cf8047774a58ada5066f398f7148262e2272308ce432964be597965921a78` |
| L03: `C03b2a/full-global-root/figures/07_global_sensitivity/forward_sensitivity_mass_within_2y_by_shock.png` | [L03](../../evidence/c03/locality/forward_sensitivity_mass_within_2y_by_shock.png) | `0de0497a5e19b00b5efe3306adedacc31897632b7e7bca5b94f65d503f692719` |

**Original scripts and workflows:**

- [scripts/experiments/sensitivity/report_forward_sensitivity_locality.py](../../scripts/experiments/sensitivity/report_forward_sensitivity_locality.py); workflow/original audit role `locality`; SHA-256 `15267683e7a5e6ac3070ebf47c98f1283384b760dcbdc4122110f20fd913088b`.

**External evidence dependencies:** `C03b2a/full-global-root/metadata/07_global_sensitivity/forward_sensitivity_locality_metadata.json`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_forward_sensitivity_dense.csv`; `C03b2a/full-global-root/tables/07_global_sensitivity/global_node_sensitivity_long.csv`.

## Artifact inventory

23 candidates retain **700,982 original bytes**. The distributed set contains **17 byte-identical originals / 393,888 bytes** and **two approved presentation derivatives / 297,723 bytes**, totaling **19 distributed exhibits / 691,611 bytes**. **Four withheld metadata originals / 13,777 bytes** remain external. These counts describe distribution, not additional financial datasets. Destinations follow the approved C04a selection; H03/H04 retain their IDs and filenames. The excluded G07 is outside these totals. Every historical original remains preserved externally. The following table records original sizes and hashes; H03/H04 public sizes and hashes appear above.

| ID | Repository exhibit or withholding decision | Original bytes | Original SHA-256 |
| --- | --- | ---: | --- |
| M01 | [simultaneous_calibration_diagnostics.csv](../../evidence/c03/methodology/simultaneous_calibration_diagnostics.csv) | 742 | `ea8873afc30ec0412eb09c8865d22d9e499407372472ad8fd833754796a03a62` |
| M02 | [three_method_global_recovery.csv](../../evidence/c03/methodology/three_method_global_recovery.csv) | 1163 | `5a948bca410d6653dac8ef4fd7d54673ecf2f756b61b85d385e5bc6e9ab1e8cb` |
| M03 | [three_method_recovery_by_horizon.csv](../../evidence/c03/methodology/three_method_recovery_by_horizon.csv) | 5087 | `420e1afa2bd0202d5a2353e833d73465cf8abd3995c2d763659e7c9990329a58` |
| M04 | WITHHELD: original JSON has local paths; summary in manifest | 1166 | `4cbd00b1237b0d1b9b605d7b2dcd2ff4f4717e9620d7e037b9c781b77202e1ed` |
| M05 | [forward_28d_recovery_three_methods.png](../../evidence/c03/methodology/forward_28d_recovery_three_methods.png) | 168893 | `50b2b01fa4e45832d731a9f0eba120cdd22a7a2627cbdf9e495fe1652a13b195` |
| Q01 | [one_sided_quote_sensitivity_summary.csv](../../evidence/c03/section05/one_sided_quote_sensitivity_summary.csv) | 2104 | `57f1a55ecd7d62c83d428338e8a59b79b1efd4d6a1b1f0b802a1ef550565f7bd` |
| Q02 | [one_sided_zero_sensitivity_matrix.csv](../../evidence/c03/section05/one_sided_zero_sensitivity_matrix.csv) | 3167 | `574a8c6cba4851c53437a3c1af16b661be5865f5909cdfba33521dd9c470f2b4` |
| Q03 | [central_quote_sensitivity_summary.csv](../../evidence/c03/section05/central_quote_sensitivity_summary.csv) | 2636 | `ff2ad6dfe8424896d1fc5ef9c4e78ce98c1a04f9d9170e3326d9c1439c5bb390` |
| Q04 | [central_zero_sensitivity_matrix.csv](../../evidence/c03/section05/central_zero_sensitivity_matrix.csv) | 3158 | `d4d7a732e21a4a06e70a254ba6b096a356edf92b5a4f67cd0e819c5e0112da1e` |
| Q05 | [own_node_local_curvature.csv](../../evidence/c03/section05/own_node_local_curvature.csv) | 1008 | `6accab217ab1c2215cd48fdf6b1b25f55c89adb4e4ee9694c1976afed79d0ca5` |
| G01 | [global_sensitivity_summary.csv](../../evidence/c03/global/global_sensitivity_summary.csv) | 19909 | `42e571ff3c58cf3a87cbeac3573818dab1329136722d38bc88ea53b899416bb9` |
| G02 | [global_calibration_diagnostics.csv](../../evidence/c03/global/global_calibration_diagnostics.csv) | 833 | `a30987b133c522a13eb73dfaf04851db4fc8d4f0b722816381cd824d00fc7f01` |
| G03 | [node_zero_sensitivity_matrix_log_linear_df.csv](../../evidence/c03/global/node_zero_sensitivity_matrix_log_linear_df.csv) | 4965 | `bef56ddcb4695f551c22a8018e51e377df868e827422ea1f9f160570000bfb64` |
| G04 | [node_zero_sensitivity_matrix_linear_continuous_zero.csv](../../evidence/c03/global/node_zero_sensitivity_matrix_linear_continuous_zero.csv) | 5051 | `6071b4c13b315f30850c2fe295640cd7fad927a68c262c87891608096212d28b` |
| G05 | [node_zero_sensitivity_matrix_cubic_continuous_zero.csv](../../evidence/c03/global/node_zero_sensitivity_matrix_cubic_continuous_zero.csv) | 5034 | `a8dc5e5da4aa9db2913ddbd70874431c2750831d3d33ad0be7c34d45b81606fb` |
| G06 | WITHHELD: original JSON has local paths; summary in manifest | 5896 | `58d40ffe14c4eabbfc8286f2b8fd3797b851a3aa0820201ed7d9310f17cb3614` |
| H01 | [forward_sensitivity_heatmap_scale_diagnostics.csv](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_scale_diagnostics.csv) | 893 | `39315d80286b50ced878b07f24b44c97213a285c4b2f72d7a3d94424dbc2a307` |
| H02 | WITHHELD: original JSON has local paths; summary in manifest | 3968 | `5ce01f5f845c3ff5b31c3e68ca8614687385e41042e04cc9c0f97f73a4f5b7d5` |
| H03 | [forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_robust_common_scale.png) | 148171 | `8d406ed6f7390f7f09d00bc8448afaecafd54b2ee71c5361672f2f8c0874adc4` |
| H04 | [forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png](../../evidence/c03/heatmaps/forward_sensitivity_heatmap_cubic_continuous_zero_full_common_scale.png) | 145146 | `4f202724ca1bcf9615cadaa22373604cc5e7a761fcfbb89f38f4be23f1038428` |
| L01 | [forward_sensitivity_locality.csv](../../evidence/c03/locality/forward_sensitivity_locality.csv) | 9411 | `de59820c13e5cbcf21d36e4ad86184eb43709192c8a7c2a14c466a18918db340` |
| L02 | WITHHELD: original JSON has local paths; summary in manifest | 2747 | `036cf8047774a58ada5066f398f7148262e2272308ce432964be597965921a78` |
| L03 | [forward_sensitivity_mass_within_2y_by_shock.png](../../evidence/c03/locality/forward_sensitivity_mass_within_2y_by_shock.png) | 159834 | `0de0497a5e19b00b5efe3306adedacc31897632b7e7bca5b94f65d503f692719` |

## Additional external audit and source records

The following archived records support grid/validation/provenance context; they were inspected, not rerun. Exact original path identities are preserved in the external C04c checkpoint. Nothing in this table is advertised as publicly downloadable.

| External evidence identity | SHA-256 |
| --- | --- |
| `C03b2b/metadata/cross-workflow-consistency.json` | `25600c94f1193bdc64ceaf242c533c48ed0a96bc63bb53ecc17bbd3e67ab8b98` |
| `C03b2b/metadata/quote-sensitivity-validation.json` | `33cced8cbf12d98bfd7bfa149ba3a15579697ac3b4201d143571c451ddb60596` |
| `C03b2a/metadata/producer-structure-validation.json` | `8496ee1962d660eed13ac0bc42c3e96bbcdbbd8935534e182a75bfb4d6273ceb` |
| `C03c/coverage-matrix.json` | `ce4b84c772fc187e3107b211bfb7d0ed6249f2794a5f23513328c9b4fdca10ca` |
| `C03c/findings.json` | `28e3298b868a0e845bd10a2273bf24e4402807507f8cb3d0da72845315abda4e` |
| `C04a/claim-evidence-matrix.md` | `fac47b86cceee6f6663ed7331dd202ec1e0fa7a59ec1a6ad43ca5cf4e6fc8889` |
| `C04a/curation-policy.md` | `c9f6fc2f55f7f48b962a853374f3ed66eb96dd4c9105b98787c51459c4e4fccd` |
| `C04a/public-evidence-architecture.md` | `02fdfdafe18eb1cc287ac5d376623dc209479d49ec0bd8e77c1e4d396b3e4928` |
| `C04a/section05-policy-proposal.md` | `45854320bf9b5eee60be46764b41e74294c2d8733baa7dcc9a6a8e38ab96b754` |
| `C04a/implementation-backlog.md` | `3c68336caa44b87627c87593e6fe4ea2aebb9390d538b014e3461b8b13ce48bb` |

<a id="external-dense-dependencies"></a>

## Dense dependencies and current availability

The compact selection is not the full 49-file global replay archive. The two original global inputs below are now included as verified lossless gzip computational dependencies in the C04d2 local review change set; see the [transport manifest](../../evidence/c03/replay-inputs.json) and [validated extraction/replay contract](reproduce.md). Both must be restored under `tables/07_global_sensitivity/` in the same new explicit reports root. Original global identifiers in the claim dependency lists above retain their historical archival meaning; their bytes are now available through these two archives, while metadata/audit records remain external. The M05 dense CSV remains external; its plot script recalibrates and writes that file, with no saved-data reader mode.

| External evidence identity | Bytes / data rows | SHA-256 |
| --- | ---: | --- |
| `C03b2a/full-global-root/tables/07_global_sensitivity/global_forward_sensitivity_dense.csv` | 13313113 / 70290 | `25cc79642af8acc9c6f8ddabdaaa0d10c6c7282274b36c2695032abdbeab6a40` |
| `C03b2a/full-global-root/tables/07_global_sensitivity/global_node_sensitivity_long.csv` | 84886 / 675 | `8ab114ac102b6ff382d96d69a2b32101515f5da6f12f41a2c6db563984f63e1c` |
| `C03b2b/reports/C/plot_three_interpolation_methods/tables/06_interpolation_comparison/forward_28d_recovery_three_methods_dense.csv` | 283195 / 1563 | `bc642f52b9b654c5e8274d055adddac89080e2f50738dfed334a175e2a5be87e` |

## Rejected extensions

Reject claims of observed-market calibration, real portfolio monetary DV01, portfolio P&L/gamma, hedge effectiveness, multi-curve validation or production readiness. The evidence also rejects universal cubic superiority/locality rankings, historical Section 05 identity, a complete public consumer replay archive and cross-platform bitwise guarantees. G07 is excluded; signed tables support the retained interpretation. Saturated heatmap colors do not reveal exact tail responses. A normalized absolute sensitivity mass is not a probability.

C04b and C04c are merged on main; see the [current publication state](index.md#publication-state). Historical pre-PR records and original rendering identities remain unchanged. C04d2 locally integrates the verified computational dependencies and scoped saved-data replay, pending external PR review. No staging, commit, push, PR creation, release or website deployment occurred in this task; C05/C06 remain separate.
