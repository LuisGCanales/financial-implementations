# Assumptions, Scope and Limitations

This document distinguishes the **implemented financial model**, the **conditions of its research experiments**, and the conclusions that its validation does—and does not—support. Contractual conventions are specified separately in [F-TIIE OIS Conventions](conventions.md); the selected calibration methodology is explained in [Methodology](methodology.md).

## Instrument and curve scope

The implementation constructs term structures from **MXN F-TIIE Overnight Indexed Swaps (OIS)**, with explicit MXMC calendar handling, ACT/360, 28-day coupon schedules, compounded overnight observations, and payment-date conventions.

The curve's reference date is the common effective date of the calibration instruments. Calibration pillars use final **payment dates**, rather than contractual maturities, so the cash flows required for repricing fall within the supported curve domain.

The project assumes a single curve for both projected F-TIIE payments and discounting:

$$
P_{\mathrm{projection}}(t)
=
P_{\mathrm{discount}}(t)
=
P(t).
$$

This isolates OIS construction and calibration mechanics. It is **not** a representation of the full MXN implied-discounting or collateral-specific architecture used in institutional markets. The present implementation does not construct a separate USD-collateralized MXN discount curve.

## Data and calendar coverage

The reproducible demonstration uses frozen **synthetic F-TIIE OIS par quotations**, not observed market quotes. The underlying synthetic reference curve is generated separately and is used **after calibration** to evaluate recovery, not as an input to the calibration engine.

Its smooth, non-flat reference term structure deliberately allows controlled comparisons of interpolation and calibration methods. Because the scenario is smooth, it can favor representations with similar smoothness. Recovery under this design does not establish performance with sparse, noisy, regime-changing, or observed market data.

The verified holiday dataset covers 2026. Long-dated synthetic experiments use a deterministic **projected MXMC calendar** for later years; its future holiday dates are a project model, not an authoritative CME, CNBV, or BMV holiday calendar. The supplied calendar's name or declared coverage does not authenticate its contents.

Synthetic instrument-tenor labels are resolved using project-defined month/year offsets before date adjustments; that mapping has not been independently verified as a replica of CME's production tenor-resolution rules.

[Calendar sources and limits](../data/calendars/README.md) · [Synthetic inputs](../data/synthetic/README.md) · [Input contract](input_contract.md)

## Calibration, interpolation and sensitivity

The selected baseline uses **simultaneous nodal calibration** with **natural cubic interpolation of continuously compounded zero rates**. The implementation also provides sequential bootstrapping and alternative interpolation methods for compatible construction and research.

A natural cubic spline is globally coupled. Perturbing one quotation may change the interpolated curve and forward rates across maturities. Existing synthetic sensitivity experiments reveal differences in response propagation, localization, and long-end amplification. These patterns depend on method, shock tenor, sampling range, and metric; they are **not** a claim that cubic interpolation is always less local for every instrument.

PCHIP is implemented as an experimental alternative, but is not part of the selected baseline or the saved three-method selection evidence.

Instrument fit alone does not identify a unique curve between calibration pillars. Even near-exact repricing can coexist with differences in implied forward rates or recovery of the synthetic reference curve.

[Interpolation methods](interpolation.md) · [Method comparison](evidence/methodology.md) · [Sensitivity results](evidence/risk.md)

## Acceptance and model suitability

The standard baseline separates solver convergence from **acceptance for use**. It checks inputs and declared calendar coverage, curve structure, finite positive discount factors, and repricing of independently reconstructed calibration instruments against specified tolerances.

This repricing is independent of saved optimizer residuals **within the same codebase**; it is not an external vendor benchmark or independent verification of the underlying pricing model.

Passing acceptance checks does **not** authenticate market quotes or holidays, demonstrate liquidity or economic suitability, establish unique recovery of an unobserved true curve, or certify production readiness. Synthetic known-truth recovery is research evidence, not a standard acceptance criterion.

The curve rejects requests outside its calibrated date range; automatic extrapolation is not supported.

[Validation and acceptance](validation.md) · [Evidence and limitations](evidence/index.md) · [Integration contract](integration_contract.md)
