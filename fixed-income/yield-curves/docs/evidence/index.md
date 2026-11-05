# C04b valuation evidence subset

Review draft for the synthetic MXN F-TIIE OIS Core-v1 project. This is the **C04b valuation subset**, with eleven original exhibits; the wider C04 collection remains incomplete. Original financial computations belong to C03. C04b curates existing bytes and performs static checks only.

**Snapshot publication: `BLOCKED_PENDING_REVIEW`.** Two machine-specific absolute paths in S07 prevent distributing the complete accepted snapshot unchanged. The original accepted seven-file snapshot remains complete, unchanged and externally archived. S03, S05 and S06 are available as standalone original payload exhibits; they are not a partial snapshot archive and cannot be passed to snapshot assurance. Original acceptance metadata, execution bindings and assurance logs remain external, so acceptance and execution bindings are not fully independently inspectable from this public collection.

| Read | Purpose |
| --- | --- |
| [Valuation narrative](valuation.md) | Synthetic inputs, construction, independent repricing, acceptance, original assurance and recovery limits |
| [Claims C01–C06](claims-valuation.md) | Supported wording, public availability, methods, units and original source hashes |
| [Valuation manifest](../../evidence/c03/valuation-manifest.json) | Portable provenance, eleven copied exhibits, four undistributed originals, withheld archive status and original workflow identities |

Publicly inspectable exhibits include the [15 synthetic calibration inputs S03](../../evidence/c03/valuation/input_quotes.csv), [15 calibrated nodes S05](../../evidence/c03/valuation/curve_nodes.csv), [15 independent repricing observations S06](../../evidence/c03/valuation/quote_repricing.csv), [projected calendar input I01](../../evidence/c03/inputs/projected_mxmc_2026_2057.csv), [bootstrap validation B01](../../evidence/c03/bootstrap/curve_validation_summary.csv), [independent repricing B02](../../evidence/c03/bootstrap/independent_repricing.csv), [zero-issue table B03](../../evidence/c03/bootstrap/validation_issues.csv), and [recovery tables and figure B04–B07](valuation.md#h-fit-versus-known-truth-recovery). “Publicly inspectable” means included at repository-relative paths in this local review draft; no release or publication has occurred.

Original sources use commit `bee31fd0883660f171ebe84817b98641239eae5b`. Independent repricing is within one codebase. All results use `FTIIE_KNOWN_TRUTH_V1`, synthetic quotes, a projected MXMC calendar and same-curve projection/discounting. They support project-scoped evidence, with no observed-market certification or production-readiness conclusion. Original logs and assurance receipts are retained externally and are not public downloads. Reproduction limits appear in the [valuation narrative](valuation.md#i-limitations-and-next-evidence-layers).
