"""Independent pricing utilities for canonical F-TIIE OIS instruments.

Pricing is intentionally separated from:

- instrument construction;
- curve calibration;
- market-data ingestion.

This module consumes already-constructed instruments and externally
provided projection / discount curves.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .curves import DiscountFactorCurve
from .instruments import (
    FTiieOIS,
    FixedLegCoupon,
    FloatingLegCoupon,
)
from .observations import OvernightObservation


@dataclass(frozen=True, slots=True)
class ProjectedOvernightRate:
    """Curve-implied simple rate for one overnight observation."""

    observation: OvernightObservation

    start_discount_factor: float
    end_discount_factor: float

    rate: float

    growth_factor: float


@dataclass(frozen=True, slots=True)
class ProjectedFloatingCoupon:
    """Projected floating coupon before discounting."""

    period_number: int

    compounded_growth_factor: float
    compounded_return: float

    amount: float

    projected_observations: tuple[
        ProjectedOvernightRate,
        ...
    ]


@dataclass(frozen=True, slots=True)
class DiscountedCashFlow:
    """One discounted contractual cash flow."""

    period_number: int

    payment_date: object

    undiscounted_amount: float
    discount_factor: float
    present_value: float


@dataclass(frozen=True, slots=True)
class OISValuationResult:
    """Present-value result for an F-TIIE OIS.

    NPV convention:

        receive floating
        pay fixed

    Therefore:

        NPV = floating_leg_pv - fixed_leg_pv
    """

    fixed_leg_pv: float
    floating_leg_pv: float

    npv_receive_float_pay_fixed: float

    par_rate: float

    fixed_cashflows: tuple[
        DiscountedCashFlow,
        ...
    ]

    floating_cashflows: tuple[
        DiscountedCashFlow,
        ...
    ]


def project_overnight_rate(
    *,
    observation: OvernightObservation,
    projection_curve: DiscountFactorCurve,
) -> ProjectedOvernightRate:
    """Project one overnight F-TIIE observation from a curve.

    The simple rate over [T1, T2] is:

        F
        =
        [P(T1) / P(T2) - 1]
        /
        alpha

    Therefore:

        1 + F * alpha
        =
        P(T1) / P(T2)

    This identity later allows the compounded floating coupon to
    telescope across consecutive overnight observations.
    """

    p_start = projection_curve.discount_factor(
        observation.accrual_start_date
    )

    p_end = projection_curve.discount_factor(
        observation.accrual_end_date
    )

    if p_start <= 0 or p_end <= 0:
        raise ValueError(
            "Projection discount factors must be positive."
        )

    rate = (
        p_start / p_end - 1.0
    ) / observation.accrual_factor

    if not isfinite(rate):
        raise ValueError(
            "Projected overnight rate must be finite."
        )

    growth_factor = (
        1.0
        + rate * observation.accrual_factor
    )

    return ProjectedOvernightRate(
        observation=observation,
        start_discount_factor=p_start,
        end_discount_factor=p_end,
        rate=rate,
        growth_factor=growth_factor,
    )


def project_floating_coupon(
    *,
    coupon: FloatingLegCoupon,
    projection_curve: DiscountFactorCurve,
) -> ProjectedFloatingCoupon:
    """Project one F-TIIE compounded floating coupon.

    Core v1 supports calibration instruments with zero floating spread.

    Spread-bearing projected OIS coupons are intentionally deferred
    until their contractual treatment is separately specified.
    """

    if coupon.spread != 0.0:
        raise NotImplementedError(
            "Core-v1 projected pricing currently supports "
            "zero floating spread only."
        )

    projected_observations: list[
        ProjectedOvernightRate
    ] = []

    compounded_growth_factor = 1.0

    for observation in coupon.observations:
        projected = project_overnight_rate(
            observation=observation,
            projection_curve=projection_curve,
        )

        projected_observations.append(
            projected
        )

        compounded_growth_factor *= (
            projected.growth_factor
        )

    compounded_return = (
        compounded_growth_factor - 1.0
    )

    amount = (
        coupon.notional
        * compounded_return
    )

    return ProjectedFloatingCoupon(
        period_number=coupon.period_number,
        compounded_growth_factor=(
            compounded_growth_factor
        ),
        compounded_return=compounded_return,
        amount=amount,
        projected_observations=tuple(
            projected_observations
        ),
    )


def discount_fixed_coupon(
    *,
    coupon: FixedLegCoupon,
    discount_curve: DiscountFactorCurve,
) -> DiscountedCashFlow:
    """Discount one fixed-leg cash flow."""

    df = discount_curve.discount_factor(
        coupon.payment_date
    )

    amount = coupon.amount

    return DiscountedCashFlow(
        period_number=coupon.period_number,
        payment_date=coupon.payment_date,
        undiscounted_amount=amount,
        discount_factor=df,
        present_value=amount * df,
    )


def discount_projected_floating_coupon(
    *,
    coupon: FloatingLegCoupon,
    projection_curve: DiscountFactorCurve,
    discount_curve: DiscountFactorCurve,
) -> DiscountedCashFlow:
    """Project and discount one floating-leg coupon."""

    projected = project_floating_coupon(
        coupon=coupon,
        projection_curve=projection_curve,
    )

    df = discount_curve.discount_factor(
        coupon.payment_date
    )

    return DiscountedCashFlow(
        period_number=coupon.period_number,
        payment_date=coupon.payment_date,
        undiscounted_amount=projected.amount,
        discount_factor=df,
        present_value=projected.amount * df,
    )


def fixed_leg_pv(
    *,
    ois: FTiieOIS,
    discount_curve: DiscountFactorCurve,
) -> tuple[
    float,
    tuple[DiscountedCashFlow, ...],
]:
    """Return fixed-leg PV and discounted cash-flow details."""

    cashflows = tuple(
        discount_fixed_coupon(
            coupon=coupon,
            discount_curve=discount_curve,
        )
        for coupon in ois.fixed_leg
    )

    pv = sum(
        cashflow.present_value
        for cashflow in cashflows
    )

    return pv, cashflows


def floating_leg_pv(
    *,
    ois: FTiieOIS,
    projection_curve: DiscountFactorCurve,
    discount_curve: DiscountFactorCurve,
) -> tuple[
    float,
    tuple[DiscountedCashFlow, ...],
]:
    """Return projected floating-leg PV."""

    cashflows = tuple(
        discount_projected_floating_coupon(
            coupon=coupon,
            projection_curve=projection_curve,
            discount_curve=discount_curve,
        )
        for coupon in ois.floating_leg
    )

    pv = sum(
        cashflow.present_value
        for cashflow in cashflows
    )

    return pv, cashflows


def fixed_leg_annuity(
    *,
    ois: FTiieOIS,
    discount_curve: DiscountFactorCurve,
) -> float:
    """Return unit-rate fixed-leg PV01-style annuity.

    The quantity is:

        N * sum(alpha_i * DF(payment_i))

    Multiplying this value by the contractual fixed rate gives
    the fixed-leg present value.
    """

    return sum(
        coupon.notional
        * coupon.accrual_factor
        * discount_curve.discount_factor(
            coupon.payment_date
        )
        for coupon in ois.fixed_leg
    )


def calculate_par_rate(
    *,
    ois: FTiieOIS,
    projection_curve: DiscountFactorCurve,
    discount_curve: DiscountFactorCurve,
) -> float:
    """Return fixed rate that makes projected OIS NPV equal zero."""

    floating_pv, _ = floating_leg_pv(
        ois=ois,
        projection_curve=projection_curve,
        discount_curve=discount_curve,
    )

    annuity = fixed_leg_annuity(
        ois=ois,
        discount_curve=discount_curve,
    )

    if annuity <= 0:
        raise ValueError(
            "Fixed-leg annuity must be positive."
        )

    return floating_pv / annuity


def value_ftiie_ois(
    *,
    ois: FTiieOIS,
    projection_curve: DiscountFactorCurve,
    discount_curve: DiscountFactorCurve,
) -> OISValuationResult:
    """Value an F-TIIE OIS under explicit projection and discount curves."""

    fixed_pv, fixed_cashflows = fixed_leg_pv(
        ois=ois,
        discount_curve=discount_curve,
    )

    floating_pv, floating_cashflows = (
        floating_leg_pv(
            ois=ois,
            projection_curve=projection_curve,
            discount_curve=discount_curve,
        )
    )

    par_rate = calculate_par_rate(
        ois=ois,
        projection_curve=projection_curve,
        discount_curve=discount_curve,
    )

    npv = (
        floating_pv
        - fixed_pv
    )

    return OISValuationResult(
        fixed_leg_pv=fixed_pv,
        floating_leg_pv=floating_pv,
        npv_receive_float_pay_fixed=npv,
        par_rate=par_rate,
        fixed_cashflows=fixed_cashflows,
        floating_cashflows=floating_cashflows,
    )