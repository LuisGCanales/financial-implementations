# Valuation claims C01–C06

[Evidence index](index.md) · [Valuation narrative](valuation.md) · [Provenance manifest](../../evidence/c03/valuation-manifest.json)

Original C04a claim IDs and exact supported wording are preserved. Every statement is scoped to synthetic `FTIIE_KNOWN_TRUTH_V1`, trade/reference dates 2026-09-15/2026-09-18, projected MXMC coverage 2026–2057 and same-curve Core-v1. Original sources use commit `bee31fd0883660f171ebe84817b98641239eae5b`.

**Availability:** S03/S05/S06 are public as unchanged standalone original payload exhibits. The complete accepted seven-file snapshot remains complete, unchanged and externally archived; its publication is `BLOCKED_PENDING_REVIEW` because S07 contains two machine-specific paths. S01/S02/S04/S07 are not distributed. The three exhibits are not a partial snapshot archive or valid snapshot-assurance input; original acceptance and execution bindings are not fully independently inspectable from this public collection. Original assurance logs and audit records remain external and are **not publicly distributed**. Rows marked external identify evidence by checkpoint and SHA-256 without pretending to provide a download. Included links resolve to versioned evidence in this public repository; after merge, the subset will be available on `main`. Repository evidence publication is not a formal tagged release or website deployment; complete snapshot publication remains `BLOCKED_PENDING_REVIEW`.

<a id="c01"></a>

## C01

**Claim type:** observed result.

**Exact supported wording:** The explicit-input cubic build was accepted under FTIIE_STANDARD_BASELINE_ACCEPTANCE_V1, with 15 quotes, 15 nodes and 15 independent repricing PASS checks; max error 4.3853809472693683e-11 bp.

**Selected artifact IDs:** S03, S05, S06, S07.

**Methodology:** Simultaneous nodal cubic calibration; repricing reconstructs instruments independently of solver residuals. PASS tolerance 0.01 bp; FAIL tolerance 0.1 bp.

**Units:** quotes/zero rates annual decimals; DF dimensionless; errors bp.

**Limitations:** Independent means a separate repricing path in the same codebase, not an independent vendor, model validator or observed-market price.

**Public inspection boundary:** Instrument-level input S03, calibrated-node S05 and cubic repricing S06 exhibits are public, including 15 saved PASS statuses. Original acceptance metadata S07 remains external. B02 belongs to the separate sequential benchmark.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| S03 | C03b1 | `bf0041e27bd82be352cadc3b9b02257368583fe5b28cdd0fa9bd74b2c11e13a4` | [input_quotes.csv](../../evidence/c03/valuation/input_quotes.csv) — standalone unchanged original payload |
| S05 | C03b1 | `53f4e23d682cce947d722030345a118736ca06db7d77611fa53c367b99f92972` | [curve_nodes.csv](../../evidence/c03/valuation/curve_nodes.csv) — standalone unchanged original payload |
| S06 | C03b1 | `b5419630d2d4513713fed2a173c6ad7910cdf0294e4ed742796d7fe8812a3f93` | [quote_repricing.csv](../../evidence/c03/valuation/quote_repricing.csv) — standalone unchanged original payload |
| S07 | C03b1 | `7c7a14588c276ec6156f5559f3451d2efb3cecac428e3e4aaa78868c4ab9b945` | External; not publicly distributed; snapshot withheld |

<a id="c02"></a>

## C02

**Claim type:** observed result.

**Exact supported wording:** The accepted run has a schema-3.0 pointer, a matching manifest and all five hash-bound payloads.

**Selected artifact IDs:** S01, S02, S03, S04, S05, S06, S07.

**Methodology:** Pointer SHA-256 binds manifest; manifest hashes calendar, inputs, nodes, repricing and metadata.

**Units:** file-byte SHA-256; run identifiers.

**Limitations:** Snapshot publication in C02 means local snapshot publication by the original CLI. Public repository evidence availability does not publish the complete snapshot or imply a formal tagged release, website deployment, trusted timestamp or cryptographic authentication.

**Public inspection boundary:** Original complete snapshot closure remains supported by external evidence only. Standalone S03/S05/S06 rows are public, but do not establish pointer/manifest closure, original acceptance or execution bindings; no copied or publicly accepted archive is claimed.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| S01 | C03b1 | `459430609efaeea7c8f83df606a5f567bb8f7e08bc0a60941d358d79a430ca3a` | External; not publicly distributed; snapshot withheld |
| S02 | C03b1 | `10a512f1dc1db8e0b48353f443caf63c7fb67fdf06542bfb36a010f1fb7becd9` | External; not publicly distributed; snapshot withheld |
| S03 | C03b1 | `bf0041e27bd82be352cadc3b9b02257368583fe5b28cdd0fa9bd74b2c11e13a4` | [input_quotes.csv](../../evidence/c03/valuation/input_quotes.csv) — standalone unchanged original payload |
| S04 | C03b1 | `531159869288cb8f42a74b738795ac02e33ebee93dc03a6d8aa2c03449df8995` | External; not publicly distributed; snapshot withheld |
| S05 | C03b1 | `53f4e23d682cce947d722030345a118736ca06db7d77611fa53c367b99f92972` | [curve_nodes.csv](../../evidence/c03/valuation/curve_nodes.csv) — standalone unchanged original payload |
| S06 | C03b1 | `b5419630d2d4513713fed2a173c6ad7910cdf0294e4ed742796d7fe8812a3f93` | [quote_repricing.csv](../../evidence/c03/valuation/quote_repricing.csv) — standalone unchanged original payload |
| S07 | C03b1 | `7c7a14588c276ec6156f5559f3451d2efb3cecac428e3e4aaa78868c4ab9b945` | External; not publicly distributed; snapshot withheld |

<a id="c03"></a>

## C03

**Claim type:** observed result.

**Exact supported wording:** Subsequent operational rebuild and snapshot assurance both exited 0, with exact saved before/after snapshot identity.

**Selected artifact IDs:** S01, S07.

**Methodology:** Original rebuild recalibrates explicit inputs; original snapshot mode reconstructs saved nodes without calibration. No assurance rerun in C04a. No assurance was rerun in C04b.

**Units:** exit codes; bp; file bytes/modes/mtime.

**Limitations:** Original assurance evidence only; not a new C04a validation run.

**Public inspection boundary:** Original C03b1 assurance only, with no new C04b assurance. The public subset cannot independently inspect the external receipts/logs.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| S01 | C03b1 | `459430609efaeea7c8f83df606a5f567bb8f7e08bc0a60941d358d79a430ca3a` | External; not publicly distributed; snapshot withheld |
| S07 | C03b1 | `7c7a14588c276ec6156f5559f3451d2efb3cecac428e3e4aaa78868c4ab9b945` | External; not publicly distributed; snapshot withheld |
| 08-operational-rebuild-assurance.stdout.log | C03b1 | `0624e8238425b0795d76a581382620836bb0b41a58a0fde9214672892ea06735` | External; not publicly distributed |
| 09-operational-snapshot-assurance.stdout.log | C03b1 | `24d78b35d1b2c59ae73987bfde778128bfcabb88447ab316fb53309fd95cc0bb` | External; not publicly distributed |
| 08-operational-rebuild-assurance-immutability.json | C03b1 | `7419a59b580424d8211a8090ddcb042a633e9f08274d56087992fd5d2f932593` | External; not publicly distributed |
| 09-operational-snapshot-assurance-immutability.json | C03b1 | `7419a59b580424d8211a8090ddcb042a633e9f08274d56087992fd5d2f932593` | External; not publicly distributed |

<a id="c04"></a>

## C04

**Claim type:** observed result.

**Exact supported wording:** Demo and explicit-input builds have identical input/node/repricing rows; PROVIDED calendar provenance still denotes supplied projected-model content.

**Selected artifact IDs:** I01, S03, S04.

**Methodology:** Saved exact financial-row comparison; PROJECTED MXMC_PROJECTED vs PROVIDED MXMC.

**Units:** DF, annual continuous zero decimals and repricing bp.

**Limitations:** No metadata byte equality; no official long-horizon calendar or observed quotes.

**Public inspection boundary:** Projected calendar input I01 and normalized input quotes S03 are public. Serialized calendar S04 and the original demo/explicit-input comparison receipt remain external. These public exhibits alone do not establish the original financial-row comparison.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| I01 | C03b1 | `d8eb688b8d48a1de7492cc6ed150a94fe070a9424e8d2a4375e1b4e0d5406507` | [projected_mxmc_2026_2057.csv](../../evidence/c03/inputs/projected_mxmc_2026_2057.csv) |
| S03 | C03b1 | `bf0041e27bd82be352cadc3b9b02257368583fe5b28cdd0fa9bd74b2c11e13a4` | [input_quotes.csv](../../evidence/c03/valuation/input_quotes.csv) — standalone unchanged original payload |
| S04 | C03b1 | `531159869288cb8f42a74b738795ac02e33ebee93dc03a6d8aa2c03449df8995` | External; not publicly distributed; snapshot withheld |
| numerical-comparison.json | C03b1 | `a69deb890383afd54fd9459683f63ea4113ccea7b1a06cecd05da8fa482ec6ff` | External; not publicly distributed |
| projected-calendar.json | C03b1 | `df3108b5ac89414297a4917b49e95f3c37567e23ec82ad3927a38de7237f1b21` | External; not publicly distributed |

<a id="c05"></a>

## C05

**Claim type:** observed result.

**Exact supported wording:** Sequential LOG_LINEAR_DF bootstrap is VALID: 15 quotes/nodes/converged steps, 15 independent PASS checks, zero critical issues; max repricing error 4.170969125638635e-09 bp.

**Selected artifact IDs:** B01, B02, B03.

**Methodology:** Sequential bootstrap with independent repricing; zero-row issues table retains its header.

**Units:** counts and bp.

**Limitations:** Historical bootstrap validation is distinct from current cubic operational acceptance.

**Public inspection boundary:** All three selected benchmark exhibits are included unchanged. Header-only B03 is evidence of zero issue rows.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| B01 | C03b2b | `384b6ca3c2f773be9494d79b700fdf2d6e5e9b662da39f41c149b3a0b37a7dac` | [curve_validation_summary.csv](../../evidence/c03/bootstrap/curve_validation_summary.csv) |
| B02 | C03b2b | `5ff09c794314b9f40e7bac256f14719e2e9f2304ecfa0f2712ee257c3f079e29` | [independent_repricing.csv](../../evidence/c03/bootstrap/independent_repricing.csv) |
| B03 | C03b2b | `59d5d3f381cec8f000c30a4544b76ed13324504d9536f77896f8864d83bd132d` | [validation_issues.csv](../../evidence/c03/bootstrap/validation_issues.csv) |

<a id="c06"></a>

## C06

**Claim type:** interpretation.

**Exact supported wording:** Excellent quote fit can coexist with nonzero known-truth recovery errors between nodes.

**Selected artifact IDs:** B01, B04, B05, B06, B07.

**Methodology:** B05 forward_28d row: saved RMSE 3.8110099310701564 bp; B04 30Y DF difference -4.418431951883073e-05.

**Units:** rate errors bp; DF differences absolute; ppm relative.

**Limitations:** Latent truth is known only in this synthetic experiment. Figures are illustrative; grid/endpoint counts differ by workflow.

**Public inspection boundary:** All five selected exhibits are included. Nonzero synthetic recovery errors do not negate instrument-fit validation or operational acceptance.

| Artifact / original evidence ID | Original checkpoint | SHA-256 | Available evidence |
| --- | --- | --- | --- |
| B01 | C03b2b | `384b6ca3c2f773be9494d79b700fdf2d6e5e9b662da39f41c149b3a0b37a7dac` | [curve_validation_summary.csv](../../evidence/c03/bootstrap/curve_validation_summary.csv) |
| B04 | C03b2b | `6018fd6b7ee525cd0400f7b472e52c3712a4407393e977ba6116c026b0761414` | [bootstrap_node_recovery.csv](../../evidence/c03/bootstrap/bootstrap_node_recovery.csv) |
| B05 | C03b2b | `3a53c0b37b8eafb024c5c80328d43fc8c5a136746fa7359f52ee2e0b3f7bc70d` | [recovery_metrics_global.csv](../../evidence/c03/bootstrap/recovery_metrics_global.csv) |
| B06 | C03b2b | `40709f76ccf2726a1df710d87a29079a300836eca70bf31d6fb747c1efa49f83` | [recovery_metrics_by_horizon.csv](../../evidence/c03/bootstrap/recovery_metrics_by_horizon.csv) |
| B07 | C03b2b | `8a2e04ee39263d1fe158c3f2bec01711463610808c318b6a96bebedcff2c881a` | [forward_28d_recovery.png](../../evidence/c03/bootstrap/forward_28d_recovery.png) |

Source script identities, verified original execution timestamps and historical comparison limits appear in the manifest. No new computation, reference designation, market-data certification or full research replay is implied.
