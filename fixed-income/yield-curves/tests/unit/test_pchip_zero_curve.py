"""Unit tests for PCHIP continuous-zero curve interpolation."""

from __future__ import annotations

from datetime import date, timedelta
from math import exp, isfinite

import pytest

from yield_curves.curves import (
    PchipContinuousZeroCurve,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)


def discount_factor_from_zero(
    *,
    zero_rate: float,
    target_date: date,
) -> float:
    """Build a discount factor from a continuous zero rate."""

    time = (
        target_date
        - REFERENCE_DATE
    ).days / 360.0

    return exp(
        -zero_rate
        * time
    )


def build_test_curve(
) -> PchipContinuousZeroCurve:
    """Build a small non-flat PCHIP zero curve."""

    node_dates = (
        date(
            2027,
            1,
            1,
        ),
        date(
            2028,
            1,
            1,
        ),
        date(
            2029,
            1,
            1,
        ),
        date(
            2030,
            1,
            1,
        ),
    )

    node_zero_rates = (
        0.080,
        0.074,
        0.069,
        0.072,
    )

    discount_factors = tuple(
        discount_factor_from_zero(
            zero_rate=zero_rate,
            target_date=node_date,
        )
        for (
            node_date,
            zero_rate,
        ) in zip(
            node_dates,
            node_zero_rates,
        )
    )

    return PchipContinuousZeroCurve(
        reference_date=(
            REFERENCE_DATE
        ),
        node_dates=(
            node_dates
        ),
        discount_factors=(
            discount_factors
        ),
    )


def test_pchip_curve_reproduces_node_discount_factors(
) -> None:
    curve = (
        build_test_curve()
    )

    for (
        node_date,
        expected_discount_factor,
    ) in zip(
        curve.node_dates,
        curve.discount_factors,
    ):
        assert (
            curve.discount_factor(
                node_date
            )
            == pytest.approx(
                expected_discount_factor,
                rel=1e-13,
                abs=1e-14,
            )
        )


def test_pchip_curve_reference_discount_factor_is_one(
) -> None:
    curve = (
        build_test_curve()
    )

    assert (
        curve.discount_factor(
            REFERENCE_DATE
        )
        == pytest.approx(
            1.0
        )
    )


def test_pchip_curve_reproduces_node_zero_rates(
) -> None:
    node_dates = (
        date(
            2027,
            1,
            1,
        ),
        date(
            2028,
            1,
            1,
        ),
        date(
            2029,
            1,
            1,
        ),
    )

    expected_zero_rates = (
        0.080,
        0.073,
        0.070,
    )

    discount_factors = tuple(
        discount_factor_from_zero(
            zero_rate=zero_rate,
            target_date=node_date,
        )
        for (
            node_date,
            zero_rate,
        ) in zip(
            node_dates,
            expected_zero_rates,
        )
    )

    curve = (
        PchipContinuousZeroCurve(
            reference_date=(
                REFERENCE_DATE
            ),
            node_dates=(
                node_dates
            ),
            discount_factors=(
                discount_factors
            ),
        )
    )

    for (
        node_date,
        expected_zero_rate,
    ) in zip(
        node_dates,
        expected_zero_rates,
    ):
        assert (
            curve.zero_rate(
                node_date
            )
            == pytest.approx(
                expected_zero_rate,
                rel=1e-13,
                abs=1e-14,
            )
        )


def test_pchip_zero_curve_preserves_flat_zero_curve(
) -> None:
    node_dates = (
        date(
            2027,
            1,
            1,
        ),
        date(
            2028,
            1,
            1,
        ),
        date(
            2029,
            1,
            1,
        ),
        date(
            2030,
            1,
            1,
        ),
    )

    flat_zero_rate = (
        0.0725
    )

    discount_factors = tuple(
        discount_factor_from_zero(
            zero_rate=(
                flat_zero_rate
            ),
            target_date=(
                node_date
            ),
        )
        for node_date
        in node_dates
    )

    curve = (
        PchipContinuousZeroCurve(
            reference_date=(
                REFERENCE_DATE
            ),
            node_dates=(
                node_dates
            ),
            discount_factors=(
                discount_factors
            ),
        )
    )

    target_dates = (
        REFERENCE_DATE
        + timedelta(
            days=90
        ),
        REFERENCE_DATE
        + timedelta(
            days=540
        ),
        REFERENCE_DATE
        + timedelta(
            days=900
        ),
        REFERENCE_DATE
        + timedelta(
            days=1300
        ),
    )

    for target_date in (
        target_dates
    ):
        assert (
            curve.zero_rate(
                target_date
            )
            == pytest.approx(
                flat_zero_rate,
                rel=1e-12,
                abs=1e-12,
            )
        )


def test_pchip_zero_curve_does_not_overshoot_monotone_nodes(
) -> None:
    """Monotone zero nodes should remain monotone between knots."""

    node_dates = (
        date(
            2027,
            1,
            1,
        ),
        date(
            2028,
            1,
            1,
        ),
        date(
            2029,
            1,
            1,
        ),
        date(
            2030,
            1,
            1,
        ),
    )

    node_zero_rates = (
        0.080,
        0.075,
        0.071,
        0.069,
    )

    discount_factors = tuple(
        discount_factor_from_zero(
            zero_rate=(
                zero_rate
            ),
            target_date=(
                node_date
            ),
        )
        for (
            node_date,
            zero_rate,
        ) in zip(
            node_dates,
            node_zero_rates,
        )
    )

    curve = (
        PchipContinuousZeroCurve(
            reference_date=(
                REFERENCE_DATE
            ),
            node_dates=(
                node_dates
            ),
            discount_factors=(
                discount_factors
            ),
        )
    )

    for interval_index in range(
        len(
            node_dates
        )
        - 1
    ):
        left_date = (
            node_dates[
                interval_index
            ]
        )

        right_date = (
            node_dates[
                interval_index
                + 1
            ]
        )

        lower_zero = min(
            node_zero_rates[
                interval_index
            ],
            node_zero_rates[
                interval_index
                + 1
            ],
        )

        upper_zero = max(
            node_zero_rates[
                interval_index
            ],
            node_zero_rates[
                interval_index
                + 1
            ],
        )

        interval_days = (
            right_date
            - left_date
        ).days

        for fraction in (
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
        ):
            target_date = (
                left_date
                + timedelta(
                    days=round(
                        interval_days
                        * fraction
                    )
                )
            )

            interpolated_zero = (
                curve.zero_rate(
                    target_date
                )
            )

            assert (
                lower_zero
                - 1e-12
                <= interpolated_zero
                <= upper_zero
                + 1e-12
            )


def test_pchip_curve_forward_rate_matches_discount_factor_identity(
) -> None:
    curve = (
        build_test_curve()
    )

    start_date = date(
        2028,
        4,
        1,
    )

    end_date = (
        start_date
        + timedelta(
            days=28
        )
    )

    start_discount_factor = (
        curve.discount_factor(
            start_date
        )
    )

    end_discount_factor = (
        curve.discount_factor(
            end_date
        )
    )

    accrual = (
        end_date
        - start_date
    ).days / 360.0

    expected_forward = (
        (
            start_discount_factor
            / end_discount_factor
            - 1.0
        )
        / accrual
    )

    assert (
        curve.forward_rate(
            start_date,
            end_date,
        )
        == pytest.approx(
            expected_forward,
            rel=1e-13,
            abs=1e-14,
        )
    )


def test_pchip_instantaneous_forward_is_finite(
) -> None:
    curve = (
        build_test_curve()
    )

    target_dates = (
        date(
            2027,
            6,
            1,
        ),
        date(
            2028,
            6,
            1,
        ),
        date(
            2029,
            6,
            1,
        ),
    )

    for target_date in (
        target_dates
    ):
        assert isfinite(
            curve.instantaneous_forward_rate(
                target_date
            )
        )


def test_pchip_curve_rejects_extrapolation_beyond_last_node(
) -> None:
    curve = (
        build_test_curve()
    )

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            curve.last_node_date
            + timedelta(
                days=1
            )
        )


def test_pchip_curve_rejects_dates_before_reference_date(
) -> None:
    curve = (
        build_test_curve()
    )

    with pytest.raises(
        ValueError,
        match="cannot precede",
    ):
        curve.zero_rate(
            REFERENCE_DATE
            - timedelta(
                days=1
            )
        )


def test_pchip_curve_requires_at_least_two_nodes(
) -> None:
    node_date = date(
        2027,
        1,
        1,
    )

    with pytest.raises(
        ValueError,
        match="at least two",
    ):
        PchipContinuousZeroCurve(
            reference_date=(
                REFERENCE_DATE
            ),
            node_dates=(
                node_date,
            ),
            discount_factors=(
                discount_factor_from_zero(
                    zero_rate=0.07,
                    target_date=(
                        node_date
                    ),
                ),
            ),
        )


def test_pchip_curve_rejects_nonpositive_discount_factor(
) -> None:
    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        PchipContinuousZeroCurve(
            reference_date=(
                REFERENCE_DATE
            ),
            node_dates=(
                date(
                    2027,
                    1,
                    1,
                ),
                date(
                    2028,
                    1,
                    1,
                ),
            ),
            discount_factors=(
                0.93,
                0.0,
            ),
        )