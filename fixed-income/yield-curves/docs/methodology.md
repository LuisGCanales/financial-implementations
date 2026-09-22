## Sequential OIS Bootstrap

Given ordered par OIS quotes:

```text
K1, K2, ..., Kn
```

the curve is calibrated sequentially.

For instrument `i`, all previous discount-factor nodes are fixed.

The next unknown state variable is:

```text
P(T0, pillar_i)
```

A candidate terminal discount factor is appended to the existing curve and
all intermediate values are generated using log-linear discount-factor
interpolation.

The candidate curve is used for both:

```text
projection
and
discounting
```

under the Core-v1 same-curve assumption.

The scalar calibration equation is:

```text
NPV_i(candidate DF) = 0
```

A bracketed Brent solver determines the discount factor satisfying the
equation.

After convergence, the node is frozen and calibration proceeds to the next
instrument.
