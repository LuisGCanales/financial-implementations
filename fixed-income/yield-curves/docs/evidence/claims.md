# Evidence Claims and Their Financial Scope

This register connects the project's **financial and methodological conclusions** to their saved results, original evidence identities, stated assumptions and reproduction boundaries.

Each claim ID is a **stable audit reference**, not a stage of model development or a sequence required for reading the research. For interpretation, begin with the [valuation](valuation.md), [interpolation](methodology.md) and [risk](risk.md) narratives. Use the specialized claim records when checking precise numerical values, original CSV/figure identities and missing evidence.

[Research evidence overview](index.md) · [Unified machine index](../../evidence/c03/index.json) · [Reproduction contract](reproduce.md)

## Financial questions and supported claims

| Question | Claim references | Scope |
|---|---|---|
| **Can the curve reprice its synthetic OIS instruments?** | [C01](claims-valuation.md#c01), [C05](claims-valuation.md#c05) | Selected simultaneous baseline and separate sequential construction; independent repricing within one codebase |
| **What is established about accepted, archived executions?** | [C02](claims-valuation.md#c02), [C03](claims-valuation.md#c03), [C04](claims-valuation.md#c04) | Original snapshot closure, assurance and input/provenance comparisons; complete bound archive remains external |
| **Does quote fit imply recovery of the true synthetic curve?** | [C06](claims-valuation.md#c06), [C07](claims-methodology-risk.md#c07), [C08](claims-methodology-risk.md#c08) | Known-reference recovery, calibrated curve roles, and three-method interpolation comparisons |
| **How do individual quote shocks move nodes and forwards?** | [C09](claims-methodology-risk.md#c09), [C10](claims-methodology-risk.md#c10), [C11](claims-methodology-risk.md#c11), [C12](claims-methodology-risk.md#c12) | Sequential and simultaneous finite differences, observed responses and cross-maturity propagation |
| **How should visual scales and locality be interpreted?** | [C13](claims-methodology-risk.md#c13), [C14](claims-methodology-risk.md#c14) | Heatmap clipping, finite forward-start grids and tenor-dependent normalized sensitivity mass |

**Evidence availability.** The public collection consists of **30 selected exhibits**: 28 byte-identical original files and two approved heatmap presentation derivatives. Eight selected original metadata/archive files remain withheld; the complete accepted operational snapshot and original assurance receipts are **not publicly downloadable**. The two compressed global-sensitivity inputs are **computational dependencies**, not additional financial exhibits.

These results depend on **synthetic F-TIIE OIS quotations, projected MXMC dates and same-curve projection/discounting**. They do not certify observed market inputs, independent vendor pricing, a multi-curve model, portfolio P&L or production readiness.

## Additional reproducibility statements

The following records **C15–C17** preserve separately reviewed statements about exact numerical comparisons, original runtime, saved-data replay and source identities. Unlike C01–C14, they are **scoped provenance/reproducibility proposals** rather than previously approved financial-result claims. Their original external checkpoint names and SHA-256 hashes are retained solely for audit, not as links to downloadable files.

<a id="c15"></a>

## C15 — Recorded numerical agreement

**Reviewed proposal; historical exact-comparison evidence only.** Original C03c reconciliation reports 101,067/101,067 saved observations in 26 byte-identical CSV pairs, and 497,304/497,307 exact global numeric cells, with only three elapsed-time cells differing. This statement describes those historical comparisons, not a C04d2 rerun of every financial workflow. Complete comparison receipts remain external and are not publicly downloadable:

| Original external identity | SHA-256 |
| --- | --- |
| `C03c/metadata/reconciliation.json` | `255251ad90ec073a9eb856547d147e1f0d116450106b68a6347bece1c298ec0b` |
| `C03b2b/metadata/historical-numerical-comparisons.json` | `8e1f44b05574f8a6f6a464c022b5d892bf1d1fd0185e033ecf9be33ce7a43b99` |
| `C03b2a/metadata/full-historical-numerical-comparison.json` | `b3a482a6bf4295cdbd029ebd35aa2807d0cbe976285979f065e010cedb56ed86` |

<a id="c16"></a>

## C16 — Saved-data replay and computational cost

**Reviewed proposal; historical runtime and scoped saved-data replay.** The original global producer took 4,802.487169651984 seconds for three base plus 90 shocked calibrations. Its external receipt `C03b2a/metadata/full-producer.json` has SHA-256 `838059712718ee347b3bf88de61e8a4aced103ccbd553ec7bb6f19111da0789a`. Duration is an observation, not a performance guarantee.

The recorded saved-data replay verified both published transport identities and recovered raw bytes, then ran the current heatmap and locality CLIs once each against the same new explicit reports root. Both exited 0 and produced the expected 27 files including inputs. H01 (four rows keyed by scope/method) and L01 (45 rows keyed by method/shock index) passed exact saved-value comparison in the recorded reference environment. This **Level-2 saved-data replay** reuses original sensitivity values; it is not recalibration and does not reproduce optimizer history. The [recipe, source/environment and limits](reproduce.md) define the supported scope. New complete execution receipts/renders remain in the external C04d2 review package; no external checkpoint link is offered as a public download.

<a id="c17"></a>

## C17 — Source, environment and rendering identities

**Reviewed proposal; separate provenance identities.** Original financial execution used `bee31fd0883660f171ebe84817b98641239eae5b` and recorded Python 3.11.15, NumPy 2.4.6, SciPy 1.17.1 and Matplotlib 3.11.2. Original environment receipt `C03c/metadata/environment.json` has SHA-256 `e6a632dc9817d496035885435fbfc9240ed1f5a2f61b115fb501310dcc091401` and remains external.

C04b integration is `39f24aff2e2c5e13d2eb53ab43d4fee53cc18dae`; C04c integration and C04d2 replay source are `d9a79eac35a8224ee8633b56b8441d0a53d0a74c`. The current heatmap renderer's SHA-256 is `3c3844dd9f133f88199fd4de1c2d48ede9de499ee1d0dabbcbc612b496a6c4e8`. Approved H03/H04 derivatives were originally rendered with that uncommitted C04c-F01 working-tree revision; their historical rendering timestamp/source remains authoritative in the [original manifest](../../evidence/c03/methodology-risk-manifest.json). Current committed source, new render execution/bytes, original financial source and repository integrations are distinct. No C04d2 integration commit existed at the index's recorded curation time; this historical fact does not describe later Git integration. Recorded versions are not fresh-install or cross-platform proof.

The numerical comparisons, runtime observations and source identities above are **audit claims with bounded reproducibility scope**, not additional evidence of observed markets, monetary portfolio risk, multi-curve validation or production readiness.
