# Curve Interpolation Methods

Interpolation determines discount factors and implied interest rates **between calibrated maturities**. It is a separate modeling choice from the calibration algorithm: different interpolators can reprice the same OIS quotations while generating different zero rates, forward-rate shapes, and sensitivities.

The curve stores positive discount factors $P_i$ at dated calibration pillars $t_i$, with $P(0)=1$. For $t>0$, the continuously compounded zero rate is

$$
z(t)=-\frac{\ln P(t)}{t},
\qquad
P(t)=e^{-t z(t)}.
$$

Time is measured using ACT/360 from the curve reference date. See [Methodology](methodology.md) for calibration objectives and experimental method selection.

## Available representations

| Financial method | Interpolated quantity | Instantaneous forward behavior | Sequential bootstrap | Simultaneous calibration |
|---|---|---|---|---|
| **Log-linear discount factors** | $\ln P(t)$ between consecutive pillars | Piecewise constant, with possible jumps at pillars | Supported | Supported |
| **Linear continuously compounded zero rates** | $z(t)$, piecewise linear | Continuous within intervals; may jump at knots because $z'(t)$ changes | Supported | Supported |
| **Natural cubic interpolation of continuous zero rates** | $z(t)$, natural cubic spline | Continuous and smooth across internal knots; globally coupled | Not supported | Supported; **selected baseline** |
| **Shape-preserving piecewise cubic interpolation (PCHIP) of continuous zero rates** | $z(t)$, locally shape-preserving cubic | Continuous; derivative behavior differs from the natural spline | Not supported | Supported; **experimental** |

The corresponding code identifiers, in the order above, are `LOG_LINEAR_DF`, `LINEAR_CONTINUOUS_ZERO`, `CUBIC_CONTINUOUS_ZERO`, and `PCHIP_CONTINUOUS_ZERO` in [`CurveInterpolationMethod`](../src/yield_curves/curves.py). Supported combinations are enforced by [`engine_capabilities.py`](../src/yield_curves/engine_capabilities.py).

### Log-linear discount factors

For a maturity $t$ between pillars $t_i$ and $t_{i+1}$, let $w=(t-t_i)/(t_{i+1}-t_i)$. Then

$$
\ln P(t)=(1-w)\ln P_i+w\ln P_{i+1}.
$$

Each interval depends only on its endpoints. This **locality** is compatible with a sequential bootstrap that fixes earlier nodes. Its implied instantaneous forward is constant within each interval, but can change abruptly at a pillar. A continuous discount-factor curve therefore does not necessarily imply a continuous instantaneous-forward curve.

### Linear continuous zero rates

The nodal discount factors are converted to continuous zero rates and interpolated linearly:

$$
z(t)=(1-w)z_i+wz_{i+1},
\qquad
P(t)=e^{-t z(t)}.
$$

This representation keeps the zero curve continuous and supports sequential construction. The instantaneous forward satisfies

$$
f(t)=z(t)+t z'(t)
$$

where differentiable; changes in the slope of $z(t)$ at knots can therefore generate jumps in instantaneous forwards. This differs from interpolating log discount factors, even when both methods match the same nodal values.

### Natural cubic interpolation of continuous zero rates

A natural cubic spline interpolates the continuous zero rates. The implementation anchors the reference-date zero rate to the **first calibrated zero rate**, because $P(0)=1$ does not itself identify $z(0)$. It then constructs a spline through the anchor and calibrated zero-rate nodes, using natural boundary conditions.

The resulting $z(t)$ and its first derivative are continuous across internal knots, so the instantaneous forward $f(t)=z(t)+t z'(t)$ is continuous.

Unlike the two local representations above, a natural cubic spline is **globally coupled**: adding or changing a distant node can change the spline between earlier nodes. The implemented calibration therefore solves the nodal discount factors **simultaneously**, rather than extending and freezing the curve one pillar at a time.

Smoothness is not sufficient evidence of financial suitability. Global coupling may spread quote sensitivities across maturities, with consequences for interpreting curve risk.

### Shape-preserving piecewise cubic interpolation (PCHIP)

PCHIP interpolates the nodal continuous zero rates using a shape-preserving piecewise cubic method. Its local construction is intended to limit overshoot relative to an unconstrained global cubic spline, but does not by itself establish superior financial or risk behavior.

It is implemented for **simultaneous calibration and experimentation**. The sequential bootstrap does not support it, and the saved three-method recovery study does **not** include PCHIP; no comparable performance conclusion is claimed.

## Financial interpretation and use

All representations are fitted to the same instrument conventions and use nodal discount factors as calibrated state. The selection affects **between-pillar discount factors, zero rates, implied forwards, and quote sensitivities**—not merely the appearance of a plotted curve.

The project's standard consumer interface selects **simultaneous nodal calibration with natural cubic interpolation of continuous zero rates**. Other supported combinations can be evaluated through the lower-level calibration functions, without inheriting the standard baseline's acceptance contract automatically.

Curves do not extrapolate past their final calibrated payment pillar. Methodological comparisons should hold the calibration engine, instruments, and inputs fixed when the purpose is to isolate the effect of interpolation.

[Financial methodology](methodology.md) · [Experimental comparison](evidence/methodology.md) · [Quote-sensitivity evidence](evidence/risk.md) · [Usage and API](integration_contract.md)
