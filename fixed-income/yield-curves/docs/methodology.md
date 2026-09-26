# Methodology

This document describes the implemented curve-construction paths and the
selection of the current project baseline. The selection is scoped to this
implementation and is not a universal ranking of interpolation methods.

## Historical sequential bootstrap

The sequential bootstrap solves one discount-factor node at a time. Previously
solved nodes remain fixed while the next terminal discount factor is found by
a bracketed Brent solve.

The historical benchmark uses:

```text
state: discount factors
interpolation: linear in log discount factors
engine: sequential bootstrap
```

For each instrument, the candidate curve is used for both projection and
discounting under the Core-v1 same-curve assumption. The scalar condition is:

```text
NPV_i(candidate discount factor) = 0
```

This path remains useful as a transparent benchmark and as the default initial
guess for simultaneous calibration. It is historical development evidence,
not the current operational baseline acceptance workflow.

## Current operational construction

The operational API calibrates all nodal discount factors simultaneously:

```text
state: nodal discount factors
engine: simultaneous nodal calibration
interpolation: CUBIC_CONTINUOUS_ZERO
```

The solver minimizes instrument repricing residuals expressed in basis points.
The implementation uses the historical sequential bootstrap only to obtain a
coherent initial guess when one is not supplied. The final solution is built
with the requested cubic representation.

At a node with ACT/360 time $t_i$ and discount factor $P_i$:

```text
z_i = -log(P_i) / t_i
```

Between nodes, the cubic representation interpolates continuous zero rates
with a natural cubic spline. For the resulting zero-rate function:

```text
P(t) = exp(-z(t) t)
f(t) = z(t) + t z'(t)
```

The continuous zero rate and its first derivative are continuous across
internal knots, producing a smooth instantaneous-forward representation.

Projection and discounting use the same curve in Core v1:

```text
projection_curve = discount_curve
```

This is a project assumption, not a claim that it reproduces the full
institutional MXN implied-discounting architecture.

## Why cubic is not sequentially frozen

A cubic spline is globally coupled: changing a later node can change the
interpolated curve on earlier intervals. Therefore the strict sequential
freeze used by log-linear local interpolation is not appropriate for this
representation. The nodal state is solved simultaneously instead.

## Method-selection evidence

Existing synthetic evidence compares repricing, recovery, forward shape, and
sensitivity behavior. Under the smooth `FTIIE_KNOWN_TRUTH_V1` scenario:

- cubic recovery of discount factors, zero rates, and forwards was very strong;
- instrument repricing was practically exact;
- the forward representation was smooth;
- global coupling reduced locality of quote responses;
- forward sensitivity propagated more broadly and was amplified at the long end.

These results support the current engineering choice under the studied scope.
They do not establish that cubic is universally superior, production-optimal,
or robust for every market regime.

Perfect calibration is not true-curve recovery. A curve can reprice all input
instruments while differing from the latent curve between nodes because the
interpolation representation and assumptions determine that behavior.

The synthetic scenario itself is smooth and therefore favors methods capable of
representing comparable smoothness. Real-market robustness is outside the
current evidence base.

## Current selection rationale

`CUBIC_CONTINUOUS_ZERO` with simultaneous nodal calibration is the
project-selected baseline for the current implementation because it offers the
most useful balance for the present synthetic study: exact repricing, strong
recovery, and smooth forwards, with known and documented sensitivity trade-offs.

PCHIP is implemented as an experimental extension. It is not part of the
current baseline or the current method-selection conclusion.

## Configuration status

`config/mxn_ftiie_ois.yaml` preserves the earlier descriptive convention
profile, including its log-linear interpolation entry. The operational API
does not load that YAML file, so the entry is not an effective runtime switch
for the current cubic baseline. It remains useful as a documented project
specification and historical configuration reference; it is intentionally not
silently rewritten to claim runtime control it does not have.
