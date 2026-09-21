# MXN F-TIIE OIS Conventions

## Purpose

This document defines the financial conventions used by the canonical
MXN F-TIIE OIS implementation.

It translates the higher-level financial specification into an explicit
instrument-convention profile that can be implemented and tested.

The objective is to prevent material financial assumptions from remaining
hidden inside code, third-party libraries, or default date-handling behavior.

---

## 1. Provenance Labels

Each convention is classified using one of the following labels.

### `SOURCE`

The convention follows an external market or institutional reference.

### `PROJECT DECISION`

The implementation deliberately chooses a methodology that is not claimed
to be an external market-standard requirement.

### `ASSUMPTION`

The implementation intentionally simplifies a more complex institutional
financial architecture.

### `INFERENCE`

The specification combines information from multiple sources where the
exact project representation is not stated verbatim in one source.

---

# 2. Canonical Instrument

Instrument:

> **MXN F-TIIE Overnight Index Swap**

Currency:

```text
MXN
```

Floating benchmark:

```text
TIIE de Fondeo
```

Floating-index representation:

```text
MXN-TIIE ON-OIS Compound
```

Underlying benchmark tenor:

```text
1D / overnight
```

**Provenance:** `SOURCE`
**References:** S1, S2

---

# 3. Core-v1 Curve Architecture

The canonical implementation constructs an:

> **F-TIIE projection curve**

from F-TIIE OIS market quotes.

For Core v1, the same curve is also used for discounting:

```text
projection_curve = discount_curve
```

**Provenance:** `ASSUMPTION`

This is a project simplification.

It is not intended to reproduce the full CME MXN implied-discounting
architecture.

The software architecture must nevertheless keep projection and discount
curve interfaces logically separable so that a future multi-curve extension
can replace:

```text
projection_curve = discount_curve
```

with:

```text
projection_curve != discount_curve
```

without redesigning the OIS instrument itself.

---

# 4. Institutional Discounting Boundary

The project explicitly distinguishes the Core-v1 same-curve assumption from
the cleared MXN implied-discounting architecture described by CME.

The broader architecture may depend on:

```text
USD SOFR
+
USD/MXN FX instruments
+
SOFR/F-TIIE cross-currency swaps
```

to construct an MXN implied discounting curve.

**Provenance:** `SOURCE`
**References:** S4, S5, S6

This architecture is outside Core v1.

---

# 5. Convention Table

| Attribute                     | Canonical value                  | Provenance       | Reference |
| ----------------------------- | -------------------------------- | ---------------- | --------- |
| Currency                      | MXN                              | SOURCE           | S2        |
| Benchmark                     | F-TIIE                           | SOURCE           | S1        |
| Floating index                | MXN-TIIE ON-OIS Compound         | SOURCE           | S2        |
| Floating tenor                | 1D                               | SOURCE           | S2        |
| Effective-date lag            | T+2 business days                | SOURCE           | S2        |
| Calendar                      | Mexico City / MXMC               | SOURCE           | S2        |
| Day count                     | ACT/360                          | SOURCE           | S2        |
| Payment frequency             | 28D                              | SOURCE           | S2, S7    |
| Calculation frequency         | 28D                              | SOURCE           | S2        |
| Reset frequency               | 28D                              | SOURCE           | S2        |
| Roll convention               | NONE                             | SOURCE           | S2        |
| Start-date adjustment         | FOLLOWING                        | SOURCE           | S2        |
| Maturity adjustment           | FOLLOWING                        | SOURCE           | S2        |
| Calculation-period adjustment | FOLLOWING                        | SOURCE           | S2        |
| Payment relative to           | END PERIOD                       | SOURCE           | S2        |
| Payment adjustment            | FOLLOWING                        | SOURCE           | S2        |
| Payment lag                   | 2 business days                  | SOURCE           | S2        |
| Fixing offset                 | 0D                               | SOURCE           | S2        |
| Fixing day type               | Business                         | SOURCE           | S2        |
| Fixing adjustment             | PRECEDING                        | SOURCE           | S2        |
| Floating compounding          | Spread Exclusive / ISDA Standard | SOURCE           | S2        |
| Floating spread               | 0                                | PROJECT DECISION | —         |
| Calibration notional          | 1                                | PROJECT DECISION | —         |
| Curve reference date          | Effective date                   | PROJECT DECISION | —         |
| Core-v1 projection curve      | F-TIIE curve                     | SOURCE-ALIGNED   | S4, S5    |
| Core-v1 discount curve        | Same F-TIIE curve                | ASSUMPTION       | —         |

---

# 6. Date Model

The implementation must distinguish the following dates explicitly:

```text
trade_date

valuation_date

effective_date

calculation_period_start

calculation_period_end

fixing_date

payment_date

maturity_date
```

No generic `date` variable should represent multiple financial concepts.

---

# 7. Trade and Effective Dates

For the canonical spot-starting OIS:

```text
effective_date
=
trade_date + 2 MXMC business days
```

**Provenance:** `SOURCE`
**Reference:** S2

Example:

```text
Trade date:
Monday

Tuesday:
business day +1

Wednesday:
business day +2

Effective date:
Wednesday
```

Actual results depend on the MXMC holiday calendar.

---

# 8. Curve Reference Date

Core v1 defines:

```text
curve_reference_date = effective_date
```

and:

```text
P(T0, T0) = 1
```

where:

```text
T0 = effective_date
```

**Provenance:** `PROJECT DECISION`

### Rationale

This separates:

```text
valuation date → effective date
```

from the actual spot-starting OIS calibration problem.

It also makes the synthetic known-truth calibration case easier to define
and validate independently.

If a valuation-date discount factor is later required, the short bridge
should be modeled explicitly rather than hidden inside the curve bootstrap.

---

# 9. 28-Day Period Structure

The canonical OIS uses:

```text
Payment Frequency = 28D

Calculation Frequency = 28D

Reset Frequency = 28D
```

**Provenance:** `SOURCE`
**References:** S2, S7

This must not be confused with the tenor of the benchmark itself.

The distinction is:

```text
Benchmark:
overnight F-TIIE

Coupon period:
28 calendar days, subject to applicable date conventions
```

---

# 10. Accrual Convention

The canonical day-count convention is:

```text
ACT/360
```

**Provenance:** `SOURCE`
**Reference:** S2

For dates:

```text
T_start
T_end
```

the year fraction is:

```text
actual calendar days between T_start and T_end
------------------------------------------------
                       360
```

The implementation must not assume that every adjusted coupon period has:

```text
tau = 28 / 360
```

because calendar adjustments can alter actual accrual dates.

---

# 11. Business-Day Adjustments

Canonical conventions:

```text
Start Date:
FOLLOWING

Maturity:
FOLLOWING

Calculation Period:
FOLLOWING

Payment:
FOLLOWING
```

**Provenance:** `SOURCE`
**Reference:** S2

The implementation should expose each convention independently even where
several currently have the same value.

Do not collapse them into a single global:

```text
business_day_convention
```

because different instrument variants may eventually require different
rules.

---

# 12. Payment Date

For each coupon period:

```text
payment_date
=
adjusted period end
+
2 MXMC business days
```

subject to the specified payment convention.

**Provenance:** `SOURCE`
**Reference:** S2

Therefore:

```text
period_end != payment_date
```

in general.

The two dates must be represented separately.

---

# 13. Fixing Convention

Canonical fixing attributes:

```text
floating tenor:
1D

fixing offset:
0D

fixing day type:
Business

fixing adjustment:
PRECEDING
```

**Provenance:** `SOURCE`
**Reference:** S2

The fixing schedule must remain distinct from the coupon-payment schedule.

---

# 14. Overnight Compounding

The floating coupon represents compounded overnight F-TIIE observations
over the applicable interest period.

Conceptually:

```text
Growth
=
Π_j (1 + r_j × d_j / 360)
```

where:

```text
r_j
=
applicable overnight F-TIIE fixing

d_j
=
number of calendar days to which that fixing applies
```

**Provenance:** `SOURCE`
**References:** S5, S7

The floating coupon on unit notional is therefore conceptually:

```text
CF_float
=
Growth - 1
```

subject to the exact contractual implementation.

---

# 15. Weekends and Holidays

F-TIIE is a business-day fixing.

For non-business calendar days, the relevant previous fixing applies for
the corresponding number of calendar days.

Example:

```text
Friday fixing
        ↓
Friday
Saturday
Sunday
```

where appropriate under the MXMC calendar.

Therefore, overnight compounding must use actual calendar-day weights rather
than treating every fixing as exactly one day.

**Provenance:** `SOURCE`
**References:** S5, S7

---

# 16. Fixed Leg

For each fixed-leg coupon period:

```text
CF_fixed,i
=
N × K × alpha_i
```

where:

```text
N
=
notional

K
=
fixed contractual rate

alpha_i
=
ACT/360 accrual fraction
```

Core calibration uses:

```text
N = 1
```

**Provenance:** `PROJECT DECISION`

### Rationale

Par-rate calibration is invariant to a common notional scale.

Unit notional therefore removes an unnecessary parameter from calibration.

---

# 17. Floating Spread

Canonical calibration instruments use:

```text
floating_spread = 0
```

**Provenance:** `PROJECT DECISION`

### Rationale

Core v1 calibrates standard par F-TIIE OIS rather than bespoke swaps
containing an additional contractual spread.

The instrument representation should nevertheless allow a floating spread
to be added later.

---

# 18. Calibration Instrument Universe

Project calibration tenors:

```text
1M
2M
3M
6M
9M
1Y
2Y
3Y
4Y
5Y
7Y
10Y
15Y
20Y
30Y
```

The 1M and 2M F-TIIE OIS inputs reflect the CME curve-input change effective
May 18, 2026.

**Provenance for 1M / 2M:** `SOURCE`
**Reference:** S3

The longer OIS structure derives from the published F-TIIE conversion-curve
methodology.

**Provenance:** `SOURCE + INFERENCE`
**References:** S3, S4

For this implementation, the complete set above is frozen as the project
calibration universe.

**Provenance:** `PROJECT DECISION`

---

## 19. Market-Tenor Resolution

For the synthetic reference framework, calibration labels such as:

```text
1M
2M
3M
...
30Y
```

are mapped to unadjusted contractual maturity dates using calendar-month
or calendar-year offsets from the effective date.

Examples:

```text
effective date + 1M
effective date + 12M
effective date + 30Y
```

Business-day adjustment is then performed by the normal instrument
schedule logic.

**Provenance:** `PROJECT DECISION`

This convention is sufficient for the controlled synthetic calibration
experiment.

It is not yet claimed to reproduce the exact maturity-generation logic
used by CME's production curve helpers. The convention must be independently
verified before using observed CME market quotes in the real-market case.


## 20. Long-Horizon Calendar Policy

The frozen `mxmc_2026.csv` dataset contains verified 2026 holiday data.

Long-dated synthetic instruments require calendar coverage beyond currently
verified annual datasets.

For synthetic experiments only, the project therefore uses a deterministic:

```text
MXMC_PROJECTED
```

calendar that extrapolates recurring Mexican financial-sector holiday rules.

**Provenance:** `PROJECT CALENDAR MODEL`

The projected calendar:

* reproduces the verified 2026 holiday set;
* provides deterministic long-horizon schedule generation;
* is not represented as an official CNBV, CME, or BMV calendar for future
  years;
* must not replace verified calendar data in the real-market implementation.

---

# 21. Curve-State Representation

The canonical calibrated curve state is represented using:

```text
discount factors
```

**Provenance:** `PROJECT DECISION`

Par OIS quotes are calibration observations.

They are not treated as the underlying curve state.

---

# 22. Zero-Rate Convention

Zero rates are reported using continuously compounded rates:

```text
R(T0,T)
=
-ln(P(T0,T)) / tau(T0,T)
```

**Provenance:** `PROJECT DECISION`

This is a reporting convention.

It does not imply that F-TIIE OIS market quotes use continuous compounding.

---

# 23. Forward-Rate Convention

For a period:

```text
[T1,T2]
```

with ACT/360 year fraction:

```text
tau(T1,T2)
```

the simple forward derived from the curve is:

```text
F(T0;T1,T2)
=
[
    P(T0,T1) / P(T0,T2)
    - 1
]
/
tau(T1,T2)
```

**Provenance:** mathematical definition used by the project.

Every forward output must include its period and rate convention.

---

# 24. Interpolation

Canonical interpolation:

```text
target:
ln(P(T))

method:
piecewise linear
```

Equivalent description:

> log-linear interpolation of discount factors.

**Provenance:** `PROJECT DECISION`

### Rationale

The method is selected as a transparent baseline because it is:

* simple to inspect;
* deterministic;
* directly related to discount factors;
* easy to test;
* suitable for studying interpolation-induced forward behavior.

It is not claimed to reproduce CME or Bloomberg production interpolation.

---

# 25. Extrapolation

Core-v1 policy:

```text
automatic extrapolation = disabled
```

**Provenance:** `PROJECT DECISION`

Requests beyond the supported calibration horizon must fail explicitly.

Expected condition:

```text
OUT_OF_CURVE_RANGE
```

---

# 26. Core-v1 Simplification Summary

The canonical implementation deliberately assumes:

```text
F-TIIE projection curve
=
discount curve
```

This is:

```text
ASSUMPTION
```

not:

```text
CME methodology
```

The objective is to isolate and validate curve-construction mechanics before
introducing the institutional multi-curve discounting architecture.

---

# 27. Future Multi-Curve Extension

The future architecture may separate:

```text
F-TIIE Projection Curve
```

from:

```text
MXN Implied Discount Curve
```

with the latter incorporating dependencies such as:

```text
USD SOFR
USD/MXN FX
SOFR/F-TIIE CCS
```

**Provenance:** `SOURCE-INSPIRED FUTURE DESIGN`
**References:** S4, S5, S6

This extension is explicitly outside Core v1.

---

# 28. Implementation Requirement

No material convention documented above should rely solely on a third-party
library default.

Code should make the intended value visible.

For example, prefer conceptually:

```python
day_count = ACT_360
payment_lag = 2
payment_adjustment = FOLLOWING
```

over:

```python
swap = SomeLibrarySwap(...)
```

where important financial behavior is inherited implicitly.

---

# 29. Testing Requirement

Every convention that changes generated dates or cash flows should receive
an explicit test.

Minimum convention tests:

```text
T+2 effective date

MXMC holiday handling

28D schedule generation

FOLLOWING adjustment

ACT/360 year fraction

2-business-day payment lag

fixing-date logic

weekend carry in overnight compounding
```

The test suite should verify financial behavior, not only code execution.

---

# 30. Source Register

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
