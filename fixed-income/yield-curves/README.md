# Yield-Curve Bootstrapping & Validation

A transparent implementation of interest-rate curve construction, calibration, and validation for financial valuation workflows.

The project focuses on the complete reasoning chain between market instruments and a curve that can be safely consumed downstream:

```text
Market Quotes
        ↓
Instrument Definitions
        ↓
Financial Conventions
        ↓
Schedules & Cash Flows
        ↓
Calibration
        ↓
Discount Factors
        ↓
Zero & Forward Rates
        ↓
Independent Repricing
        ↓
Curve Diagnostics
        ↓
Validated Curve
```

The objective is not simply to produce a curve that fits market quotes.

The objective is to build a curve whose:

* financial inputs;
* conventions;
* assumptions;
* calibration;
* numerical behavior;
* implied forwards;
* limitations;
* and validation status

can be inspected and defended.

---

## Current Status

**Phase:** Canonical implementation foundation
**Status:** In development
**Version:** 0.1.0

Current development is focused on the financial foundation required before calibration:

```text
conventions
↓
business calendar
↓
schedule construction
↓
overnight observations
↓
OIS representation
↓
calibration
```

The project should not yet be interpreted as a completed pricing or production curve engine.

---

## Canonical Market

The primary implementation targets the Mexican interest-rate market using:

> **MXN F-TIIE Overnight Index Swaps**

The canonical benchmark is:

> **TIIE de Fondeo / F-TIIE**

The floating leg references the overnight F-TIIE process and market-standard OIS conventions are represented explicitly rather than inherited silently from third-party library defaults.

Detailed conventions are documented in:

```text
docs/conventions.md
```

Machine-readable configuration is stored in:

```text
config/mxn_ftiie_ois.yaml
```

---

## Core-v1 Financial Architecture

The primary curve constructed by the project is an:

> **F-TIIE projection curve**

For Core v1, the implementation deliberately uses the same curve for both projection and discounting:

```text
projection_curve = discount_curve
```

This is an explicit **project simplification**.

It is not intended to reproduce the complete institutional MXN implied-discounting architecture used for cleared derivatives.

The simplification allows the project to isolate and validate:

```text
instrument mechanics
+
curve construction
+
interpolation
+
repricing
+
diagnostics
```

before introducing cross-currency dependencies.

---

## Institutional Boundary

The project explicitly distinguishes its Core-v1 same-curve assumption from the broader MXN discounting architecture documented for cleared derivatives.

A future advanced implementation may separate:

```text
F-TIIE Projection Curve
```

from:

```text
MXN Implied Discount Curve
```

with the latter potentially depending on:

```text
USD SOFR
+
USD/MXN FX instruments
+
SOFR/F-TIIE cross-currency swaps
```

That multi-curve architecture is outside the initial implementation scope.

---

## Canonical Calibration Universe

The project calibration universe is:

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

using MXN F-TIIE OIS instruments.

The numerical contemporary market snapshot will be frozen separately.

Implementation development begins from a deterministic synthetic known-truth dataset so that calibration correctness can be tested independently of external market-data availability.

---

## Financial Conventions

The canonical OIS profile includes:

| Attribute              | Value                            |
| ---------------------- | -------------------------------- |
| Currency               | MXN                              |
| Benchmark              | F-TIIE                           |
| Floating index         | MXN-TIIE ON-OIS Compound         |
| Floating tenor         | 1D                               |
| Effective date         | T+2 business days                |
| Calendar               | Mexico City / MXMC               |
| Day count              | ACT/360                          |
| Payment frequency      | 28D                              |
| Calculation frequency  | 28D                              |
| Reset frequency        | 28D                              |
| Roll convention        | NONE                             |
| Start-date adjustment  | FOLLOWING                        |
| Maturity adjustment    | FOLLOWING                        |
| Calculation adjustment | FOLLOWING                        |
| Payment adjustment     | FOLLOWING                        |
| Payment lag            | 2 business days                  |
| Fixing offset          | 0D                               |
| Fixing adjustment      | PRECEDING                        |
| Compounding            | ISDA Standard / Spread Exclusive |

Each convention is documented together with its provenance in:

```text
docs/conventions.md
```

---

## Curve Representation

The canonical curve state is represented using:

> **discount factors**

Derived outputs include:

```text
discount factors
zero rates
period forward rates
par OIS rates
```

Continuous compounding is used for zero-rate reporting.

This is a project reporting convention and should not be confused with the quotation convention of the calibration instruments.

---

## Interpolation

The Core-v1 interpolation baseline is:

> **piecewise linear interpolation in log discount factors**

or equivalently:

> **log-linear discount-factor interpolation**

This is a project methodology choice rather than a claim about CME or Bloomberg production methodology.

The baseline is intentionally transparent and will be compared against alternative approaches.

Planned challenger methods include:

```text
linear interpolation in continuously compounded zero rates

cubic-spline interpolation in par swap / OIS rates
```

The comparison is intended to study how interpolation choices affect:

```text
discount factors
zero rates
forward rates
local sensitivity
calibration behavior
```

---

## Validation Philosophy

Calibration and validation are treated as separate problems.

A curve reproducing its calibration instruments is not automatically considered reliable.

The project therefore evaluates:

```text
market-input integrity

schedule correctness

calibration convergence

instrument repricing

discount-factor validity

zero-rate behavior

implied forward behavior

interpolation effects

input sensitivity

failure scenarios
```

A central project principle is:

> **Correct repricing of calibration instruments is necessary but not sufficient evidence that a curve is financially or numerically well behaved.**

---

## Curve Validation States

The curve engine will expose three technical states:

```text
VALID
REVIEW
INVALID
```

### VALID

Calibration and required structural validations pass.

### REVIEW

Calibration succeeds, but diagnostics identify behavior requiring analyst judgment.

Examples may include:

```text
unusual forward behavior
unexpected local sensitivity
large cross-day movement
non-critical methodology warnings
```

### INVALID

A critical condition prevents safe downstream use.

Examples include:

```text
missing required input
undefined convention
calibration failure
invalid discount factor
repricing failure
unsupported extrapolation
```

An invalid curve should not proceed automatically into downstream valuation.

---

## Independent Validation

The calibration routine should not be the sole proof that the curve is correct.

The project will use:

```text
native calibration engine
        ↓
curve object
        ↓
independent OIS repricer
```

and later an external benchmark such as:

> **QuantLib**

QuantLib is intended as a challenger implementation rather than the hidden canonical engine.

---

## Synthetic Known-Truth Case

A deterministic synthetic reference case will be used to validate the full calibration process.

Conceptually:

```text
Known Underlying Curve
        ↓
Generate Theoretical OIS Quotes
        ↓
Hide Original Curve
        ↓
Calibrate From Quotes
        ↓
Recover Curve
        ↓
Compare Against Known Truth
```

This allows the project to test calibration accuracy against an actual ground truth.

Synthetic inputs will always be labeled explicitly as synthetic data.

---

## Legacy TIIE28 Case

The repository will also preserve a historical TIIE28 case originating from earlier financial-engineering coursework and independent reconstruction.

Its purpose is not to represent the current Mexican benchmark environment.

It is retained to investigate:

```text
legacy interpolation methods
forward-rate indexing
curve-shape behavior
methodological differences
```

A particular focus will be reproducing and explaining suspicious forward behavior observed in the earlier implementation.

---

## Repository Structure

```text
yield-curves/
│
├── config/
│   ├── mxn_ftiie_ois.yaml
│   └── sample_curve.yaml
│
├── data/
│   ├── README.md
│   └── sample/
│
├── docs/
│   ├── assumptions_limitations.md
│   ├── conventions.md
│   ├── integration_contract.md
│   ├── interpolation.md
│   ├── methodology.md
│   └── validation.md
│
├── notebooks/
│   ├── 01_curve_demo.ipynb
│   ├── 02_interpolation_comparison.ipynb
│   └── 03_curve_diagnostics.ipynb
│
├── reports/
│   └── sample_outputs/
│
├── src/
│   └── yield_curves/
│       ├── conventions.py
│       ├── calendars.py
│       ├── schedules.py
│       ├── instruments/
│       ├── quotes/
│       ├── bootstrap/
│       ├── interpolation/
│       ├── curves/
│       ├── validation/
│       ├── diagnostics/
│       └── utilities/
│
├── tests/
│   ├── unit/
│   ├── calibration/
│   ├── regression/
│   └── fixtures/
│
├── CHANGELOG.md
├── NOTES.md
├── pyproject.toml
└── README.md
```

---

## Installation

Python 3.11 or later is required.

Create an isolated environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Upgrade packaging tools:

```bash
python -m pip install --upgrade pip
```

Install the project in editable development mode:

```bash
python -m pip install -e ".[dev]"
```

---

## Running Tests

From the project root:

```bash
pytest
```

For compact output:

```bash
pytest -q
```

The test suite is intended to include several different levels of validation:

```text
unit tests
calibration tests
financial-property tests
regression tests
failure scenarios
```

---

## Current Development Milestone

The first financial implementation milestone is:

> **construct a spot-starting F-TIIE OIS schedule correctly before attempting curve calibration.**

The initial implementation therefore focuses on:

```text
T+2 effective date

MXMC business-day logic

28D calculation periods

FOLLOWING adjustment

ACT/360 accrual factors

2-business-day payment lag

overnight fixing / observation logic
```

Only after these mechanics are independently validated will curve calibration begin.

---

## Data Policy

Project data should clearly distinguish between:

```text
OBSERVED MARKET DATA

SYNTHETIC DATA

LEGACY / HISTORICAL DATA

DERIVED CURVE OUTPUT
```

Synthetic inputs should never be presented as observed market quotes.

The reproducible Core-v1 demonstration should not depend on proprietary live-market infrastructure.

---

## Scope

Core v1 is intended to demonstrate:

```text
financial-instrument understanding
explicit conventions
curve construction
numerical calibration
interpolation analysis
repricing
curve diagnostics
sensitivity analysis
independent validation
```

It is not intended to represent:

```text
production banking infrastructure
a proprietary pricing engine
a Bloomberg curve replica
a CME production-engine replica
live trading infrastructure
institutional deployment
```

---

## Documentation

Detailed project documentation is separated by responsibility:

```text
docs/conventions.md
→ contractual and market conventions

docs/methodology.md
→ financial derivations and calibration equations

docs/interpolation.md
→ interpolation methodology and comparison

docs/validation.md
→ validation framework and status logic

docs/assumptions_limitations.md
→ simplifications and scope boundaries

docs/integration_contract.md
→ interface with downstream valuation projects
```

---

## Primary References

### Banco de México — TIIE de Fondeo

[https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF111](https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CF111)

### CME — MXN F-TIIE OIS Market Standard Attributes

[https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf](https://www.cmegroup.com/articles/files/2024/f-tiie-ois-market-standard-attributes.pdf)

### CME Clearing Advisory 26-167 — F-TIIE Curve Input Changes

[https://www.cmegroup.com/notices/clearing/2026/05/26-167.html](https://www.cmegroup.com/notices/clearing/2026/05/26-167.html)

### CME — F-TIIE OIS Conversion Curve Construction

[https://www.cmegroup.com/articles/files/2024/FTIIE-conversion-curve-methodology.pdf](https://www.cmegroup.com/articles/files/2024/FTIIE-conversion-curve-methodology.pdf)

### CME — Conversion Pricing for Cleared MXN 28D TIIE Swaps

[https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf](https://www.cmegroup.com/articles/files/2024/mxn-pricing.pdf)

### CME Clearing Advisory 25-005 — MXN Discounting Curve Input Changes

[https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2025/01/chadv25-005.pdf](https://www.cmegroup.com/content/dam/cmegroup/notices/clearing/2025/01/chadv25-005.pdf)

---

## Relationship to Broader Work

This implementation is intended to become a reusable financial component.

For example:

```text
Yield-Curve Bootstrapping & Validation
        ↓
Validated Curve Object
        ↓
MXN Valuation & Price Validation Engine
```

The yield-curve implementation owns:

```text
curve methodology
construction
validation
diagnostics
```

while downstream applications own:

```text
instrument valuation
workflow controls
exceptions
reporting
analyst decisions
```

This separation allows the curve methodology to evolve independently from the applications that consume it.

---

## Project Principle

The objective is not merely:

> **build a yield curve.**

It is:

> **build a yield curve and know when not to trust it.**
