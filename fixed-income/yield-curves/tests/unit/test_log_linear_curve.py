from datetime import date
from math import exp, log

import pytest

from yield_curves.curves import (
    LogLinearDiscountCurve,
)


REFERENCE = date(
    2026,
    1,
    1,
)


def test_reference_df_is_one() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE,
        node_dates=(
            date(2026, 4, 1),
        ),
        discount_factors=(
            0.98,
        ),
    )

    assert curve.discount_factor(
        REFERENCE
    ) == pytest.approx(1.0)


def test_curve_returns_exact_node_values() -> None:
    nodes = (
        date(2026, 4, 1),
        date(2026, 7, 1),
    )

    dfs = (
        0.98,
        0.96,
    )

    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE,
        node_dates=nodes,
        discount_factors=dfs,
    )

    assert curve.discount_factor(
        nodes[0]
    ) == pytest.approx(
        dfs[0]
    )

    assert curve.discount_factor(
        nodes[1]
    ) == pytest.approx(
        dfs[1]
    )


def test_interpolation_is_linear_in_log_df() -> None:
    left = date(
        2026,
        1,
        1,
    )

    midpoint = date(
        2026,
        2,
        15,
    )

    right = date(
        2026,
        4,
        1,
    )

    right_df = 0.96

    curve = LogLinearDiscountCurve(
        reference_date=left,
        node_dates=(
            right,
        ),
        discount_factors=(
            right_df,
        ),
    )

    # 45 days from Jan-1 to Feb-15
    # 90 days from Jan-1 to Apr-1
    weight = 45 / 90

    expected_log_df = (
        weight * log(right_df)
    )

    expected_df = exp(
        expected_log_df
    )

    assert curve.discount_factor(
        midpoint
    ) == pytest.approx(
        expected_df
    )


def test_log_linear_segment_implies_constant_continuous_forward() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE,
        node_dates=(
            date(2026, 4, 1),
        ),
        discount_factors=(
            0.98,
        ),
    )

    first_forward = curve.forward_rate(
        date(2026, 1, 15),
        date(2026, 1, 29),
    )

    second_forward = curve.forward_rate(
        date(2026, 2, 15),
        date(2026, 3, 1),
    )

    assert first_forward == pytest.approx(
        second_forward
    )


def test_curve_does_not_extrapolate() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE,
        node_dates=(
            date(2026, 4, 1),
        ),
        discount_factors=(
            0.98,
        ),
    )

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            date(2026, 4, 2)
        )


def test_curve_rejects_non_positive_df() -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        LogLinearDiscountCurve(
            reference_date=REFERENCE,
            node_dates=(
                date(2026, 4, 1),
            ),
            discount_factors=(
                0.0,
            ),
        )


def test_curve_rejects_unsorted_nodes() -> None:
    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        LogLinearDiscountCurve(
            reference_date=REFERENCE,
            node_dates=(
                date(2026, 7, 1),
                date(2026, 4, 1),
            ),
            discount_factors=(
                0.96,
                0.98,
            ),
        )