# Interpolation

All current nodal curves store discount factors at calibrated pillar dates.
Interpolation determines how values between those nodes are represented.

## `LOG_LINEAR_DF`

- **State representation:** nodal discount factors.
- **Interpolated quantity:** log discount factor.
- **Smoothness:** discount factor is continuous; instantaneous forward rate is piecewise constant with jumps at nodes.
- **Forward behavior:** transparent local segments with possible forward jumps.
- **Strict sequential construction:** supported.
- **Project status:** historical/canonical sequential benchmark.

## `LINEAR_CONTINUOUS_ZERO`

- **State representation:** nodal discount factors transformed to continuous zero rates.
- **Interpolated quantity:** continuous zero rate.
- **Smoothness:** zero rate is continuous and piecewise linear; forward slope changes at nodes.
- **Forward behavior:** less discontinuous than log-linear DF, but not globally smooth.
- **Strict sequential construction:** supported.
- **Project status:** challenger and experimental benchmark.

## `CUBIC_CONTINUOUS_ZERO`

- **State representation:** nodal discount factors transformed to continuous zero rates.
- **Interpolated quantity:** continuous zero rate through a natural cubic spline.
- **Smoothness:** continuous first derivative across internal knots; smooth instantaneous forwards.
- **Forward behavior:** smooth but globally coupled; quote shocks can propagate across the curve.
- **Strict sequential construction:** not supported as a reliable freeze-and-append method; use simultaneous nodal calibration.
- **Project status:** current operational baseline.

## `PCHIP_CONTINUOUS_ZERO`

- **State representation:** nodal discount factors transformed to continuous zero rates.
- **Interpolated quantity:** shape-preserving piecewise cubic continuous zero rate.
- **Smoothness:** shape-preserving cubic behavior without the same global spline coupling.
- **Forward behavior:** intended to reduce overshoot relative to unconstrained cubic interpolation.
- **Strict sequential construction:** not supported by the sequential bootstrap implementation.
- **Project status:** implemented experimental extension; excluded from the current baseline conclusions.

No additional PCHIP research is implied by this document. Existing unit tests establish implementation behavior, but no persisted PCHIP comparison evidence is used for the current selection.
