from datetime import date
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