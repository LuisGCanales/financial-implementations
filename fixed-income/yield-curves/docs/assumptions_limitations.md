# Assumptions and Limitations

## Market and instrument scope

The implementation targets MXN F-TIIE Overnight Index Swaps using the F-TIIE
overnight benchmark, explicit conventions, and an MXMC business calendar.
The detailed contractual conventions are documented in
[conventions.md](conventions.md).

## Same-curve assumption

Core v1 uses the same curve for projection and discounting:

```text
projection_curve = discount_curve
```

This is a project assumption. It is not a complete multi-curve or cleared-MXN
implied-discounting architecture.

## Synthetic demonstration data

The current reproducible demonstration uses
`data/synthetic/ftiie_ois_quotes_v1.csv`, a frozen synthetic reference dataset.
It is not observed market data, a market forecast, or a claim to replicate CME
or bank production curves.

The operational API does not depend on the synthetic truth function. The truth
is used only by research workflows to evaluate recovery.

## Coverage and extrapolation

The curve does not extrapolate beyond its final calibrated node. Consumers must
respect the calibrated coverage.

The projected MXMC calendar extends beyond the directly verified calendar data.
Future production use requires explicit calendar provenance and coverage
appropriate to the input instruments.

## Interpolation and sensitivity

The current baseline uses simultaneous nodal calibration with a natural cubic
spline in continuous zero rates. Cubic interpolation is globally coupled:
changes in one quote can affect distant curve regions.

Existing sensitivity evidence found broader quote-shock propagation, lower
forward-risk locality, and greater long-end forward-sensitivity amplification.
These are known structural trade-offs, not implementation accidents to hide.

## Synthetic known-truth bias

The smooth known-truth scenario favors representations capable of expressing
similar smoothness. Strong recovery under that scenario is useful evidence but
does not establish robustness under noisy, sparse, regime-changing, or
real-market inputs.

Perfect calibration is not equivalent to recovering a true curve between
observed instruments.

## Architecture limits

There is no multi-curve discounting architecture yet. Operational acceptance
checks numerical and structural conditions; it does not establish market-data
correctness, economic suitability, liquidity quality, or universal methodology
superiority.

PCHIP is implemented as an experimental extension but is not part of the
current selected methodology or baseline conclusion.
