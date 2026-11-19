# MXN F-TIIE Overnight Indexed Swap — Financial Conventions

This document specifies the contractual conventions used to **construct, project, and value MXN F-TIIE OIS calibration instruments**. It separates market-sourced conventions from explicit project choices and simplifying assumptions.

The project implements financial mechanics directly rather than relying on undocumented defaults in a pricing engine. The resulting curve methodology and evidence are discussed in [Methodology](methodology.md), while [Assumptions and Limitations](assumptions_limitations.md) sets out the model's boundaries.

## Instrument and convention profile

The instrument is a **Mexican-peso F-TIIE Overnight Indexed Swap**, with an overnight floating benchmark (TIIE de Fondeo), a fixed leg, and coupon calculation/payment periods based on 28-day schedules. The **overnight index tenor** must not be confused with the **28-day coupon period**.

The table distinguishes:

- **Market source:** an attribute aligned with a cited market or institutional reference.
- **Project decision:** a deliberately selected implementation or calibration convention.
- **Model assumption:** a simplification of a broader financial architecture.

| Convention | Implemented value | Basis |
|---|---|---|
| Currency | MXN | Market source [S2] |
| Floating benchmark | F-TIIE / TIIE de Fondeo (overnight) | Market source [S1, S2] |
| Floating index description | MXN-TIIE ON-OIS Compound; 1D underlying | Market source [S2] |
| Business-day calendar | Mexico City (MXMC) | Market source [S2] |
| Effective date | Trade date + 2 MXMC business days | Market source [S2] |
| Day-count basis | ACT/360 | Market source [S2] |
| Coupon calculation, payment, and reset frequency | 28 calendar days | Market source [S2, S7] |
| Schedule roll convention | None | Market source [S2] |
| Start, maturity, and period-end adjustments | Following | Market source [S2] |
| Payment date | End of adjusted period + 2 business days; Following | Market source [S2] |
| Reset relative to / adjustment | End of period; Following | Implemented descriptor |
| Fixing offset and day type | 0 business days; business-day fixings | Market source [S2] |
| Fixing adjustment | Preceding | Market source [S2] |
| Floating compounding | ISDA Standard; spread exclusive | Market source [S2] |
| Floating spread | Zero | Project decision |
| Calibration notional | One unit | Project decision |
| Curve reference date | Common OIS effective date | Project decision |
| Calibration node date | Final payment date of each OIS | Project decision |
| Projection and discounting | Same F-TIIE curve | Model assumption |

The implementation exposes a validated, **fixed** F-TIIE OIS convention profile through [`FTiieOISConventions`](../src/yield_curves/conventions.py). Its attributes are not unrestricted runtime switches. The supplied holiday calendar is a separate input: the label `MXMC` describes the required calendar family, not proof that a particular holiday dataset is complete or authoritative.

## Dates, schedules and accrual

The construction distinguishes **trade, effective, contractual maturity, adjusted maturity, calculation-period start/end, overnight fixing, and payment dates**. Their meanings are not interchangeable.

For a spot-starting OIS, the effective date is the trade date plus two MXMC business days, provided the trade date itself is a valid business day. The project's curve reference date $T_0$ is that effective date, with

$$
P(T_0,T_0)=1.
$$

Thus the calibration curve begins at the OIS effective date, not at the trade date. A discount bridge back to trade or valuation date would require a separate financial treatment.

Coupon boundaries are generated in 28-calendar-day increments from the effective date, with a final shorter period if contractual maturity is not an exact multiple of 28 days. Applicable business-day adjustments are then applied. The resulting accrual fraction is

$$
\alpha_i
=
\frac{\text{actual calendar days from adjusted start to adjusted end}}{360}.
$$

Because dates can be adjusted, $\alpha_i$ is **not always** $28/360$. Payment takes place two MXMC business days after the adjusted period end, so the accrual end and payment date generally differ.

The fixing observation schedule is distinct from the coupon-payment schedule. One fixing may cover multiple calendar days—for example, an observation beginning on Friday may accrue through the following Monday. The weights must reflect those actual calendar days, including weekends and holidays.

[Calendar data and provenance](../data/calendars/README.md) · [Schedule implementation](../src/yield_curves/schedules.py) · [Overnight observations](../src/yield_curves/observations.py)

## Cash flows, overnight compounding and par pricing

For coupon period $i$, let $N$ be notional, $K$ the fixed rate, and $\alpha_i$ the ACT/360 accrual fraction. The fixed-leg coupon amount is

$$
CF_i^{\mathrm{fixed}}=N K \alpha_i.
$$

For the floating leg, let $r_{ij}$ denote the overnight rate applicable to observation $j$ within coupon $i$, and $d_{ij}$ its associated number of calendar days. Compounded growth is

$$
G_i
=
\prod_j\left(1+r_{ij}\frac{d_{ij}}{360}\right),
$$

giving a zero-spread floating coupon amount of

$$
CF_i^{\mathrm{float}}=N(G_i-1).
$$

For projected coupons, the implementation infers each overnight rate from the projection curve over the observation's accrual interval, rather than treating the 28-day coupon as one overnight fixing.

Both legs are discounted to the curve reference date using the **payment dates**. For a receive-floating/pay-fixed position, the model's sign convention is

$$
\operatorname{NPV}
=
PV_{\mathrm{float}}
-
PV_{\mathrm{fixed}}.
$$

The par fixed rate is the rate for which the two leg values agree under the specified curve assumptions. Unit notional is used for calibration because a common notional scale does not change a par rate; valuation of supported instruments can use a different positive notional. Nonzero floating spreads are **not supported** by the current financial profile.

[Pricing implementation](../src/yield_curves/pricing.py) · [Calibration methodology](methodology.md)

## Curve-construction conventions and market-data scope

The controlled synthetic calibration example uses the following **project-selected** OIS maturities:

`1M, 2M, 3M, 6M, 9M, 1Y, 2Y, 3Y, 4Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y`.

The 1M and 2M F-TIIE OIS inputs reflect the CME curve-input change effective **18 May 2026** [S3]. Longer-tenor references draw on the published F-TIIE conversion-curve methodology [S4], but the **complete calibration basket is a project choice**, not a claim to replicate the current CME production input universe.

For synthetic generation, labels such as `3M` or `10Y` are resolved by calendar-month or calendar-year offsets from the effective date **before business-day adjustments**. This deterministic project convention has not been independently validated against CME's production maturity-generation rules.

The project uses the final **payment date** of each swap as its calibration pillar. With a two-business-day payment lag, this avoids needing a curve value beyond the last pillar to price the instrument. It is a project construction choice, not a claim about CME's internal pillar placement.

The validated 2026 holiday dataset and the **projected** future MXMC calendar serve different purposes. The latter supports controlled long-horizon synthetic experiments but must not be represented as an official long-dated market calendar.

Calibrated state consists of nodal **discount factors**. Reported zero rates are continuously compounded and forward rates over explicit periods are simple ACT/360 rates:

$$
z(T)
=
-\frac{\ln P(T_0,T)}{\tau(T_0,T)},
\qquad T>T_0,
$$

$$
F(T_1,T_2)
=
\frac{P(T_0,T_1)/P(T_0,T_2)-1}{\tau(T_1,T_2)}.
$$

These reporting conventions do not redefine the market OIS quotation convention. **Interpolation belongs to the curve methodology, not the instrument contract**; the current selected representation is natural cubic interpolation of continuous zero rates, with other implemented alternatives described in [Interpolation](interpolation.md).

Curve queries outside calibrated date coverage fail explicitly; automatic extrapolation is not supported.

## Institutional boundary and source interpretation

Projection of overnight F-TIIE cash flows and discounting of those cash flows are distinct financial functions. The current implementation uses the same curve for both as a **model assumption**. Cleared MXN implied-discounting arrangements may instead depend on USD SOFR, USD/MXN instruments, and SOFR/F-TIIE cross-currency swaps [S4–S6]. No such multi-curve construction is implemented here.

The reference sources establish the origin of specified market attributes; they do **not** certify that the whole implementation reproduces CME production curves, their holiday datasets, or their valuation methodology. Project choices and inferences remain identified as such.

For the exact coded profile and the tests of its date/cash-flow behavior, see [`conventions.py`](../src/yield_curves/conventions.py), [validation](validation.md), and the [test coverage map](test-coverage-map.md).

---

## Source Register
## S1 — Banco de México — TIIE de Fondeo a un día

[https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF111](https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF111)

Primary use:

* benchmark definition;
* official fixing;
* overnight nature of F-TIIE.

---

## S2 — CME Group — Market Standard Attributes: MXN F-TIIE Overnight Index Swaps (OIS)

[https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf](https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf)

Primary use:

* instrument conventions;
* T+2;
* MXMC;
* ACT/360;
* 28D;
* payment lag;
* fixing;
* compounding.

---

## S3 — CME Clearing Advisory 26-167 — MXN F-TIIE 1D Curve Input Changes

[https://www.cmegroup.com/notices/clearing/2026/05/26-167.html](https://www.cmegroup.com/notices/clearing/2026/05/26-167.html)

PDF:

[https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2026/05/chadv26-167.pdf](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2026/05/chadv26-167.pdf)

Primary use:

* removal of F-TIIE futures from current curve inputs;
* addition of 1M and 2M F-TIIE OIS.

---

## S4 — CME Group — F-TIIE OIS Conversion Curve Construction

[https://www.cmegroup.com/articles/files/2024/FTIIE-conversion-curve-methodology.pdf](https://www.cmegroup.com/articles/files/2024/FTIIE-conversion-curve-methodology.pdf)

Primary use:

* F-TIIE forecasting-curve structure;
* longer OIS nodes;
* MXN implied-discounting architecture;
* FX and CCS inputs.

---

## S5 — CME Group — Conversion Pricing for Cleared MXN 28D TIIE Swaps

[https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf](https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf)

Primary use:

* F-TIIE compounding mechanics;
* forecasting vs discounting;
* MXN PAA;
* USD SOFR / FX relationship.

---

## S6 — CME Clearing Advisory 25-005 — MXN Discounting Curve Input Changes

[https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2025/01/chadv25-005.pdf](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2025/01/chadv25-005.pdf)

Primary use:

* SOFR/F-TIIE CCS;
* MXN implied discount-curve input transition.

---

## S7 — Banco de México / GTTR — F-TIIE Standardized-Swap Documentation

[https://www.banxico.org.mx/mercados/grupo-de-trabajo-de-tasas-de-referencia-alternativ/d/%7B255951F6-54AB-C10D-720E-82C70BB02B30%7D.pdf](https://www.banxico.org.mx/mercados/grupo-de-trabajo-de-tasas-de-referencia-alternativ/d/%7B255951F6-54AB-C10D-720E-82C70BB02B30%7D.pdf)

Primary use:

* standardized F-TIIE swap structure;
* 28-day periods;
* overnight compounding.
