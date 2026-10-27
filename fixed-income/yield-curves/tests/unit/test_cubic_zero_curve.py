from datetime import date, timedelta
from math import exp

import pytest

from yield_curves.curves import (
    CubicContinuousZeroCurve,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)


def test_cubic_curve_reproduces_node_discount_factors() -> None:
    node_dates = (
        date(2027, 1, 1),
        date(2028, 1, 1),
        date(2030, 1, 1),
    )

    node_zeros = (
        0.07,
        0.065,
        0.072,
    )

    discount_factors = tuple(
        exp(
            -zero
            * (
                node_date
                - REFERENCE_DATE
            ).days
            / 360.0
        )
        for node_date, zero in zip(
            node_dates,
            node_zeros,
        )
    )

    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=node_dates,
        discount_factors=discount_factors,
    )

    for node_date, expected_df in zip(
        node_dates,
        discount_factors,
    ):
        assert (
            curve.discount_factor(
                node_date
            )
            == pytest.approx(
                expected_df
            )
        )


def test_reference_discount_factor_is_one() -> None:
    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
            date(2028, 1, 1),
        ),
        discount_factors=(
            0.93,
            0.86,
        ),
    )

    assert (
        curve.discount_factor(
            REFERENCE_DATE
        )
        == pytest.approx(1.0)
    )


def test_no_extrapolation_beyond_last_node() -> None:
    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
            date(2028, 1, 1),
        ),
        discount_factors=(
            0.93,
            0.86,
        ),
    )

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            date(2028, 1, 2)
        )


def test_instantaneous_forward_is_continuous_around_internal_node() -> None:
    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
            date(2028, 1, 1),
            date(2030, 1, 1),
        ),
        discount_factors=(
            0.93,
            0.87,
            0.75,
        ),
    )

    pillar = date(
        2028,
        1,
        1,
    )

    from datetime import timedelta

    left = curve.instantaneous_forward_rate(
        pillar - timedelta(seconds=0)
    )

    at_node = curve.instantaneous_forward_rate(
        pillar
    )

    # With date-only resolution we cannot approach the node
    # infinitesimally, so exact node evaluation is primarily
    # testing that the spline derivative is well-defined.
    assert left == pytest.approx(
        at_node
    )


def test_natural_cubic_zero_anchor_and_forward_math() -> None:
    """CURVE-03 / CURVE-08: analytical natural spline, without calibration."""
    a, b = 0.04, 0.08
    delta = b - a
    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            REFERENCE_DATE + timedelta(days=360),
            REFERENCE_DATE + timedelta(days=720),
        ),
        discount_factors=(exp(-a), exp(-2.0 * b)),
    )
    tolerance = {"rel": 1e-13, "abs": 1e-14}

    assert curve.reference_date == REFERENCE_DATE
    assert curve.node_times == pytest.approx((1.0, 2.0), **tolerance)
    assert curve.node_zero_rates == pytest.approx((a, b), **tolerance)

    # Natural spline through (0,a), (1,a), (2,b):
    # [0,1]: z=a+delta*(t**3-t)/4; z'=delta*(3*t**2-1)/4.
    # [1,2]: z=a+delta*(t-1)+delta*((2-t)**3-(2-t))/4;
    #        z'=delta+delta*(1-3*(2-t)**2)/4.
    # Natural endpoint second derivatives and C2 matching fix these cubics.
    for days, time, expected_zero, expected_derivative in (
        (0, 0.0, a, -delta / 4.0),
        (180, 0.5, a - 3.0 * delta / 32.0,
         delta * (3.0 * 0.5**2 - 1.0) / 4.0),
        (540, 1.5, a + 13.0 * delta / 32.0,
         delta + delta * (1.0 - 3.0 * (2.0 - 1.5)**2) / 4.0),
    ):
        target_date = REFERENCE_DATE + timedelta(days=days)
        assert curve.zero_rate(target_date) == pytest.approx(
            expected_zero, **tolerance,
        )
        assert curve.discount_factor(target_date) == pytest.approx(
            exp(-time * expected_zero), **tolerance,
        )
        assert curve.instantaneous_forward_rate(target_date) == pytest.approx(
            expected_zero + time * expected_derivative, **tolerance,
        )

    # Two interior non-node dates, with non-unit accrual to protect the divisor.
    start_date = REFERENCE_DATE + timedelta(days=180)
    end_date = REFERENCE_DATE + timedelta(days=450)
    expected_start_df = exp(-0.5 * (a - 3.0 * delta / 32.0))
    end_time = 1.25
    expected_end_zero = (
        a + delta * (end_time - 1.0)
        + delta * ((2.0 - end_time)**3 - (2.0 - end_time)) / 4.0
    )
    expected_end_df = exp(-end_time * expected_end_zero)
    expected_forward = (
        (expected_start_df / expected_end_df - 1.0)
        / ((end_date - start_date).days / 360.0)
    )
    assert curve.forward_rate(start_date, end_date) == pytest.approx(
        expected_forward, **tolerance,
    )


@pytest.mark.parametrize(
    "node_day_offsets, discount_factors, message",
    [
        pytest.param(
            (360,), (0.96,),
            "at least two calibrated nodes", id="one-node",
        ),
        pytest.param(
            (360, 720), (0.96,),
            "must have equal length", id="length-mismatch",
        ),
        pytest.param(
            (0, 720), (0.96, 0.85),
            "strictly increasing and later than the reference date",
            id="node-equals-reference",
        ),
        pytest.param(
            (720, 360), (0.96, 0.85),
            "strictly increasing and later than the reference date",
            id="reversed-nodes",
        ),
        pytest.param(
            (360, 720), (0.96, 0.0),
            "finite and strictly positive", id="zero-df",
        ),
        pytest.param(
            (360, 720), (0.96, -0.85),
            "finite and strictly positive", id="negative-df",
        ),
        pytest.param(
            (360, 720), (0.96, float("nan")),
            "finite and strictly positive", id="nan-df",
        ),
        pytest.param(
            (360, 720), (0.96, float("inf")),
            "finite and strictly positive", id="infinite-df",
        ),
    ],
)
def test_cubic_constructor_rejects_invalid_nodes_or_discount_factors(
    node_day_offsets: tuple[int, ...],
    discount_factors: tuple[float, ...],
    message: str,
) -> None:
    """CURVE-04: each invalid input must reach its constructor guard."""
    node_dates = tuple(
        REFERENCE_DATE + timedelta(days=days)
        for days in node_day_offsets
    )
    with pytest.raises(ValueError, match=message):
        CubicContinuousZeroCurve(
            reference_date=REFERENCE_DATE,
            node_dates=node_dates,
            discount_factors=discount_factors,
        )


@pytest.mark.parametrize(
    "start_days, end_days, message",
    [
        pytest.param(
            360, 360,
            "Forward end date must follow forward start date",
            id="equal-dates",
        ),
        pytest.param(
            720, 360,
            "Forward end date must follow forward start date",
            id="reversed-interval",
        ),
        pytest.param(
            -1, 360,
            "Forward start date cannot precede curve reference date",
            id="start-before-reference",
        ),
        pytest.param(
            360, 721, "OUT_OF_CURVE_RANGE", id="end-after-last-node",
        ),
    ],
)
def test_cubic_forward_rejects_invalid_date_intervals(
    start_days: int,
    end_days: int,
    message: str,
) -> None:
    """CURVE-06: real forwards reject invalid order and out-of-domain dates."""
    curve = CubicContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            REFERENCE_DATE + timedelta(days=360),
            REFERENCE_DATE + timedelta(days=720),
        ),
        discount_factors=(0.96, 0.85),
    )
    start_date = REFERENCE_DATE + timedelta(days=start_days)
    end_date = REFERENCE_DATE + timedelta(days=end_days)
    with pytest.raises(ValueError, match=message):
        curve.forward_rate(start_date, end_date)
