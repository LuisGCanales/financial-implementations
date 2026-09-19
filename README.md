# Financial Implementations

Reusable financial-methodology implementations focused on valuation, markets, risk, and financial decision support.

This repository contains focused implementations of financial models, instrument mechanics, calibration methods, risk measures, and validation controls.

The objective is not to build isolated coding exercises.

Each implementation is designed to make the full financial reasoning chain explicit:

```text
Financial Problem
        ↓
Instrument / Market Definition
        ↓
Conventions & Assumptions
        ↓
Methodology
        ↓
Implementation
        ↓
Validation
        ↓
Diagnostics
        ↓
Reusable Financial Output
```

The emphasis is on implementations that can be inspected, challenged, tested, and reused in broader financial workflows.

---

## Purpose

The repository serves as a library of independently understandable financial implementations.

Each project should answer three questions:

1. **What financial problem is being solved?**
2. **Why is the methodology financially defensible?**
3. **How do we know the implementation is behaving correctly?**

The intended signal is not simply:

> I can implement a financial formula.

It is:

> I can translate financial definitions, market conventions, and methodology into reproducible implementations and independently validate their behavior.

---

## Repository Structure

```text
financial-implementations/
│
├── fixed-income/
│   └── yield-curves/
│
├── derivatives/
│   └── ...
│
├── risk/
│   └── ...
│
└── README.md
```

Each implementation may operate as its own Python project while remaining part of the same Git repository.

This allows implementations to remain focused and independently testable without fragmenting the broader financial-methodology library across many repositories.

---

## Current Implementations

### Fixed Income

#### Yield-Curve Bootstrapping & Validation

**Status:** In development

Construction and validation of MXN interest-rate curves with explicit market conventions, calibration logic, interpolation choices, repricing controls, forward-rate diagnostics, sensitivity analysis, and independent benchmarking.

The canonical implementation focuses on the F-TIIE OIS market while preserving a historical TIIE28 case for methodology comparison and legacy-analysis purposes.

Core areas include:

* financial-instrument representation;
* calendar and schedule construction;
* OIS conventions;
* discount-factor calibration;
* zero and forward rates;
* interpolation methodology;
* calibration-instrument repricing;
* numerical diagnostics;
* input perturbation analysis;
* curve-validation states;
* independent benchmarking.

Project directory:

```text
fixed-income/yield-curves/
```

---

## Planned Areas

Future implementations may cover areas such as:

```text
Fixed Income
├── bond valuation
├── duration / modified duration
├── DV01
└── convexity

Derivatives
├── option valuation
├── Greeks
└── cross-method validation

Risk
├── market-risk measures
├── scenario analysis
└── model / methodology validation
```

New implementations should only be added when they provide a distinct financial capability rather than duplicating functionality already available elsewhere in the repository.

---

## Design Principles

### 1. Financial definitions come before code

An implementation should begin with:

```text
instrument
→ cash flows
→ conventions
→ market inputs
→ methodology
```

before software architecture is optimized.

---

### 2. Conventions must be explicit

Material assumptions should not remain hidden inside:

* library defaults;
* spreadsheet conventions;
* undocumented date logic;
* implicit rate definitions.

Where a convention comes from an external market or institutional source, that source should be identified.

Where the implementation deliberately chooses its own methodology, the choice and rationale should be documented separately.

---

### 3. Calibration is not validation

A model reproducing its calibration instruments does not automatically imply that its outputs are financially or numerically well behaved.

Validation should therefore examine, where relevant:

* repricing error;
* curve shape;
* implied forwards;
* numerical stability;
* sensitivity to market inputs;
* interpolation effects;
* failure scenarios.

---

### 4. Financial correctness and software correctness are different

Tests should distinguish between:

```text
Does the code execute correctly?

Does the numerical method behave correctly?

Does the resulting financial model behave correctly?
```

All three matter.

---

### 5. Independent validation is preferred

Where practical, implementations should be challenged through a sufficiently independent path.

Examples include:

* independent repricers;
* analytical solutions;
* alternative numerical methods;
* QuantLib benchmarks;
* known-truth synthetic datasets;
* controlled perturbation tests.

---

### 6. Reproducibility over hidden infrastructure

Core examples should be reproducible from frozen configuration and data whenever possible.

A portfolio implementation should not require proprietary market terminals, live feeds, or undocumented local state merely to demonstrate its methodology.

---

### 7. Observed, synthetic, and derived data must remain distinguishable

Outputs should clearly differentiate:

```text
OBSERVED MARKET DATA

SYNTHETIC DATA

LEGACY / HISTORICAL DATA

DERIVED MODEL OUTPUT
```

Synthetic values should never be presented as observed market quotes.

---

### 8. Failure should be explicit

Missing inputs, undefined conventions, calibration failure, unsupported extrapolation, or invalid outputs should produce visible failure states.

The preferred behavior is:

```text
fail explicitly
```

rather than:

```text
continue under a hidden assumption
```

---

## Typical Implementation Standard

Depending on the financial problem, an implementation should aim to contain:

```text
README
financial methodology
documented conventions
assumptions and limitations
reproducible sample data
canonical implementation
tests
validation diagnostics
sample outputs
independent benchmark
```

Not every project requires identical infrastructure.

The architecture should remain proportional to the financial problem being solved.

---

## Relationship to Applied Projects

Implementations in this repository are intended to be reusable building blocks.

They may be consumed by larger applied projects without duplicating methodology.

For example:

```text
Yield-Curve Bootstrapping & Validation
        ↓
validated curve object
        ↓
Valuation & Price Validation workflow
```

The financial implementation owns:

* curve construction;
* methodology;
* financial validation;
* technical diagnostics.

The consuming application owns:

* workflow integration;
* instrument valuation;
* exception management;
* reporting;
* analyst decisions.

This separation allows methodology to be improved independently from the applications that consume it.

---

## Scope

This repository is intended for financial-methodology implementations and analytical components.

It is not intended to represent:

* production banking infrastructure;
* proprietary institutional pricing systems;
* live trading systems;
* exchange or clearing-house methodology replicas unless explicitly stated;
* professional production experience where the implementation originated from independent research or coursework.

Where an implementation uses a simplified financial assumption, that assumption should be stated explicitly.

---

## Development Philosophy

The general workflow is:

```text
Understand the financial problem
        ↓
Freeze the financial specification
        ↓
Implement the mechanics
        ↓
Reprice / reproduce known results
        ↓
Test financial properties
        ↓
Investigate discrepancies
        ↓
Document limitations
        ↓
Expose a reusable interface
```

The objective is not merely to produce numerical output.

It is to produce financial implementations whose assumptions, mechanics, behavior, and limitations can be defended.