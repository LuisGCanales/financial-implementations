# Yield-Curve Construction and Calibration Methodology

This document describes the financial and numerical methodologies implemented for constructing MXN F-TIIE OIS term structures, their available configurations, and the evidence supporting the project's current method selection.

The central distinction is between **reproducing quoted instrument prices** and **obtaining a term structure with suitable behavior between calibration maturities**. Both the calibration approach and the interpolation representation affect the resulting curve.

## 1. Financial Calibration Problem

An interest-rate curve is constructed from a set of F-TIIE OIS par quotations. Each quote corresponds to an instrument whose contractual dates, coupon periods, overnight compounding, and payment cash flows are determined by the applicable [financial conventions](conventions.md).

The calibration seeks discount factors that reproduce the observed or supplied par quotations under the selected pricing assumptions.

For the current implementation, the curve reference date is the common effective date of the instruments. Calibration pillars correspond to their final payment dates, ensuring that the required discounted cash flows remain within the curve domain.

Projection and discounting use the same curve:

$$
P_{\mathrm{projection}}(t)=P_{\mathrm{discount}}(t)=P(t).
$$

This is an explicit project simplification, not a representation of a complete multi-curve or collateral-specific discounting framework.

### Curve representation

Let $P(t)$ denote the discount factor at time $t$, measured in ACT/360 years from the curve reference date.

The continuously compounded zero rate is

$$
z(t)=-\frac{\ln P(t)}{t}, \qquad t>0.
$$

Equivalently,

$$
P(t)=e^{-t z(t)}.
$$

The instantaneous forward rate implied by this representation is

$$
f(t)=z(t)+t z'(t),
$$

where the derivative exists.

The implementation also calculates simple forward rates over specified date intervals. For example, a 28-day forward rate is

$$
F(t_1,t_2)=
\frac{1}{\tau(t_1,t_2)}
\left(
\frac{P(t_1)}{P(t_2)}-1
\right),
$$

where $\tau(t_1,t_2)$ is the ACT/360 accrual fraction.

The distinction matters: instantaneous forward rates characterize the local term-structure shape, while discrete forwards correspond to rates implied over actual periods.

## 2. Calibration Approaches

The project implements two approaches for recovering discount factors from OIS par quotations.

### Sequential bootstrapping

Sequential bootstrapping calibrates instruments in increasing maturity order.

For instrument $i$, the previously calibrated discount factors $P_1,\ldots,P_{i-1}$ remain fixed, while the next discount factor $P_i$ is determined by solving

$$
\operatorname{NPV}_i(P_1,\ldots,P_i)=0.
$$

The implementation uses a bracketed Brent root solver for each instrument.

This approach offers a transparent construction process: each calibration step can be examined separately, and previously solved nodes are preserved.

It is especially useful for:

- Constructing curves with interpolation methods compatible with sequential node extension.
- Examining the relationship between individual instruments and calibrated nodes.
- Studying local calibration behavior and numerical diagnostics.
- Providing a financially coherent starting point for simultaneous calibration.

The implemented sequential solver supports log-linear interpolation of discount factors and linear interpolation of continuously compounded zero rates.

### Simultaneous nodal calibration

Simultaneous calibration determines all nodal discount factors jointly.

Let $K_i^{\mathrm{quote}}$ denote the supplied par rate of instrument $i$ and $K_i^{\mathrm{model}}$ the corresponding rate calculated from the candidate curve.

The optimization minimizes squared repricing errors, expressed in basis points:

$$
\min_{\mathbf{x}}
\sum_{i=1}^{n}
\left[
10^4
\left(
K_i^{\mathrm{model}}(\mathbf{x})
-
K_i^{\mathrm{quote}}
\right)
\right]^2,
$$

with optimization variables

$$
x_j=\ln P_j,
\qquad
P_j=e^{x_j}>0.
$$

Using log discount factors ensures positivity of the calibrated factors by construction, subject to the configured numerical bounds.

Unlike the sequential approach, every node may change during calibration. This is important when the interpolation method couples different maturity regions.

**Initialization.** When no initial discount factors are supplied, the implementation first constructs a sequential curve using log-linear discount-factor interpolation. Its calibrated nodes provide the initial guess for simultaneous optimization.

Alternatively, a caller may supply an admissible vector of discount factors, such as one obtained from a nearby calibration.

The simultaneous solver supports all currently implemented interpolation representations, although some are retained for methodological experimentation rather than selected for the standard project workflow.

## 3. Interpolation Methodologies

Calibration determines nodal values; interpolation determines how the curve behaves between them.

| Method | Financial representation | Main implications |
|---|---|---|
| **Log-linear discount factors** | Linear interpolation of $\ln P(t)$ between pillars | Local construction; piecewise-constant instantaneous forwards with possible jumps at pillars |
| **Linear continuous zero rates** | Linear interpolation of continuously compounded zero rates | Continuous zero curve, with changes in forward-rate behavior at interpolation knots |
| **Natural cubic continuous zero rates** | Natural cubic spline over continuously compounded zero rates | Smooth instantaneous forwards; global coupling between nodes |
| **Shape-preserving cubic continuous zero rates (PCHIP)** | Piecewise cubic interpolation designed to preserve local shape properties | An alternative to global cubic splines; implemented but not yet supported by comparable research evidence |

The distinction between local and globally coupled representations is particularly relevant.

With log-linear discount-factor interpolation, introducing a later node does not change the already constructed earlier segments. A natural cubic spline, by contrast, may change earlier interpolated values when a later node changes.

Consequently, the implemented natural cubic approach is calibrated simultaneously rather than through a strict sequential freeze-and-append process.

For the corresponding implementation identifiers and supported engine combinations, see [Interpolation](interpolation.md).

## 4. Experimental Evidence and Method Selection

### Controlled synthetic reference scenario

To investigate how interpolation affects the resulting term structure, the project constructs a **smooth, non-flat synthetic zero-rate curve** with a known underlying functional form.

The reference curve combines a long-run rate level, a decaying short-end component, and a medium-term curvature component:

$$
z_{\mathrm{true}}(t)
=
L+
S e^{-t/\tau_s}
+
H t e^{-t/\tau_h}.
$$

The selected parameters produce relatively elevated short-end rates, a declining intermediate region, and gradual long-end normalization.

Using the project's F-TIIE OIS conventions, this curve generates **15 synthetic par quotations spanning 1M to 30Y**.

These quotations are subsequently treated as calibration inputs for the competing methodologies. The underlying reference curve is not provided to the calibration engines; it is used afterward to measure recovery.

This separation makes it possible to investigate two different questions:

1. **Calibration accuracy:** How closely does each method reproduce its input OIS quotations?
2. **Term-structure recovery:** How closely does the calibrated curve reproduce the underlying reference discount factors, zero rates, and forward rates between pillars?

The experiment is controlled and reproducible, but its synthetic smoothness may favor methods with similar functional properties.

### Interpolation comparison

For a comparison using simultaneous nodal calibration across all three methods, the saved results show near-exact instrument repricing but materially different recovery of 28-day forwards.

| Interpolation | 28-day forward RMSE |
|---|---:|
| Log-linear discount factors | 3.811 bp |
| Linear continuous zero rates | 5.235 bp |
| Natural cubic continuous zero rates | 0.249 bp |

Natural cubic interpolation achieves the lowest forward recovery error in this scenario. It also produces a smooth instantaneous-forward representation.

However, sensitivity experiments identify an important trade-off: **global coupling allows changes in one calibration quotation to affect forward rates across a broader range of maturities**.

That behavior can reduce the locality of quote sensitivities and complicate the interpretation of curve risk.

The results therefore support a comparison across multiple criteria rather than a ranking based on repricing error alone.

[Methodology experiments](evidence/methodology.md) · [Quote sensitivity and locality](evidence/risk.md)

### Selected methodology

The current project baseline uses **simultaneous nodal calibration with natural cubic interpolation of continuously compounded zero rates**.

This selection reflects the combination of near-exact repricing, strong recovery, and smooth forward-rate behavior observed in the controlled reference scenario, while retaining the documented global-sensitivity trade-offs.

The choice is **specific to the evidence and scope of this implementation**. It does not establish that natural cubic interpolation is universally superior, optimally suited to observed MXN market data, or preferable for every valuation and risk application.

The sequential and alternative interpolation methods remain available for compatible construction tasks and methodological comparisons.

## 5. Method Configuration and Implementation

The implemented methods distinguish three separate elements:

| Element | How it is defined |
|---|---|
| **Financial conventions** | The supported F-TIIE OIS instrument profile defines calendars, accrual, coupon, fixing, and payment conventions |
| **Calibration approach** | An explicitly selected sequential or simultaneous calibration function |
| **Interpolation representation** | An explicitly selected method supported by the chosen calibration approach |

The standard consumer interface, `build_baseline_ftiie_curve`, fixes the current baseline to simultaneous nodal calibration with natural cubic interpolation of continuously compounded zero rates.

Lower-level calibration functions expose alternative interpolation methods explicitly, subject to supported engine–method combinations.

The caller supplies the OIS quotations and business calendar. The simultaneous calibration function also accepts optional initial discount factors; otherwise, it obtains its initial guess from sequential bootstrapping.

These runtime choices are defined in the Python implementation. Descriptive configuration files are not automatically interpreted as executable calibration settings.

Relevant implementation entry points:

- [`bootstrap.py`](../src/yield_curves/bootstrap.py) — sequential calibration.
- [`calibration.py`](../src/yield_curves/calibration.py) — simultaneous nodal calibration.
- [`curves.py`](../src/yield_curves/curves.py) — curve representations and interpolation.
- [`baseline.py`](../src/yield_curves/baseline.py) — selected baseline and consumer interface.
- [`engine_capabilities.py`](../src/yield_curves/engine_capabilities.py) — supported method–engine combinations.

For practical examples of API usage, input construction, and downstream consumption, see the [integration contract](integration_contract.md). Module responsibilities and execution dependencies are documented separately in [technical architecture](architecture.md).

## 6. Validation and Interpretation

Convergence of a numerical solver does not by itself establish that the resulting curve is suitable for downstream financial use.

The implementation therefore distinguishes calibration success from acceptance checks, including independent reconstruction and repricing of calibration instruments, curve-structure checks, and numerical tolerances.

Broader methodological evaluation also considers interpolated curve behavior, sensitivity propagation, and recovery under controlled scenarios.

**Perfect repricing is not equivalent to recovering a unique or economically appropriate curve between calibration maturities.**

The current experimental evidence uses synthetic quotations, a projected calendar, and a single-curve projection/discounting assumption. Real-market robustness, broader collateral-specific architectures, and performance under different market regimes require separate investigation.

[Validation and acceptance](validation.md) · [Assumptions and limitations](assumptions_limitations.md)