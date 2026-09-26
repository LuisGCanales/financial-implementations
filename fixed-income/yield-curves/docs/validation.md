# Validation and Acceptance

The project distinguishes historical bootstrap validation from acceptance of
the current operational baseline.

## Historical bootstrap validation

The historical validation workflow operates on `BootstrapResult`. It checks
quote integrity, sequential solver steps, curve structure, discount-factor
validity, and independently reprices the calibration instruments. Its outputs
are preserved under `reports/03_curve_validation/` as historical evidence.

Those reports document the sequential/log-linear path. They are not the
acceptance contract for the current cubic baseline.

## Current operational baseline acceptance

`yield_curves.baseline` calibrates with simultaneous nodal calibration and
`CUBIC_CONTINUOUS_ZERO`, then performs a baseline-specific acceptance check.

The acceptance checks:

- solver/calibration success;
- expected interpolation method;
- curve availability;
- node count equal to quote count;
- calibration check count equal to quote count;
- strictly increasing node dates;
- finite, strictly positive discount factors;
- independent reconstruction of each OIS from the input quote;
- independent recalculation of each model par rate;
- finite repricing errors;
- every independent repricing error within the PASS tolerance of `0.01 bp`.

Discount factors are not required to be strictly decreasing. That condition is
not universally valid across rate regimes.

The result exposes two different states:

```text
calibration_success
    solver found a numerical solution

accepted_for_use
    the solution also passed the operational checks above
```

Therefore:

```text
calibration_success != accepted_for_use
```

A result can converge and still be rejected for downstream use.

## What acceptance does not prove

Operational acceptance does not prove that quotes are observed-market correct,
that the curve is universally optimal, or that it matches a latent true curve.
Recovery against synthetic known truth is research evidence, not an
operational acceptance criterion.
