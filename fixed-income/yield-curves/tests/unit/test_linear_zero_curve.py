from datetime import date, timedelta
from math import exp

import pytest

from yield_curves.curves import (
    LinearContinuousZeroCurve,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)


def test_curve_reproduces_node_discount_factors() -> None:
    node_dates = (
        date(2027, 1, 1),
        date(2028, 1, 1),
    )

    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=node_dates,
        discount_factors=(
            0.93,
            0.86,
        ),
    )

    assert (
        curve.discount_factor(
            node_dates[0]
        )
        == pytest.approx(
            0.93
        )
    )

    assert (
        curve.discount_factor(
            node_dates[1]
        )
        == pytest.approx(
            0.86
        )
    )


def test_reference_date_discount_factor_is_one() -> None:
    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.93,
        ),
    )

    assert (
        curve.discount_factor(
            REFERENCE_DATE
        )
        == pytest.approx(
            1.0
        )
    )


def test_first_segment_uses_first_node_zero_rate() -> None:
    rate = 0.07

    node_date = date(
        2027,
        1,
        1,
    )

    node_time = (
        node_date
        - REFERENCE_DATE
    ).days / 360.0

    node_df = exp(
        -rate
        * node_time
    )

    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            node_date,
        ),
        discount_factors=(
            node_df,
        ),
    )

    target_date = date(
        2026,
        7,
        1,
    )

    assert (
        curve.zero_rate(
            target_date
        )
        == pytest.approx(
            rate
        )
    )


def test_zero_rate_is_linearly_interpolated() -> None:
    first_date = date(
        2027,
        1,
        1,
    )

    second_date = date(
        2029,
        1,
        1,
    )

    first_time = (
        first_date
        - REFERENCE_DATE
    ).days / 360.0

    second_time = (
        second_date
        - REFERENCE_DATE
    ).days / 360.0

    first_zero = 0.06
    second_zero = 0.08

    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            first_date,
            second_date,
        ),
        discount_factors=(
            exp(
                -first_zero
                * first_time
            ),
            exp(
                -second_zero
                * second_time
            ),
        ),
    )

    midpoint_time = (
        first_time
        + second_time
    ) / 2.0

    midpoint_days = round(
        midpoint_time
        * 360.0
    )

    midpoint_date = (
        REFERENCE_DATE
        + timedelta(
            days=midpoint_days
        )
    )

    expected_weight = (
        (
            midpoint_date
            - first_date
        ).days
        / (
            second_date
            - first_date
        ).days
    )

    expected_zero = (
        first_zero
        + expected_weight
        * (
            second_zero
            - first_zero
        )
    )

    assert (
        curve.zero_rate(
            midpoint_date
        )
        == pytest.approx(
            expected_zero
        )
    )


def test_constant_node_zeros_produce_flat_zero_curve() -> None:
    rate = 0.07

    node_dates = (
        date(2027, 1, 1),
        date(2028, 1, 1),
        date(2030, 1, 1),
    )

    discount_factors = tuple(
        exp(
            -rate
            * (
                node_date
                - REFERENCE_DATE
            ).days
            / 360.0
        )
        for node_date in node_dates
    )

    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=node_dates,
        discount_factors=(
            discount_factors
        ),
    )

    test_dates = (
        date(2026, 6, 1),
        date(2027, 7, 1),
        date(2029, 1, 1),
    )

    for target_date in test_dates:
        assert (
            curve.zero_rate(
                target_date
            )
            == pytest.approx(
                rate
            )
        )


def test_curve_does_not_extrapolate() -> None:
    curve = LinearContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.93,
        ),
    )

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            date(
                2027,
                1,
                2,
            )
        )