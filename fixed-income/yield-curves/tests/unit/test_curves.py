from datetime import date
from math import exp

import pytest

from yield_curves.curves import (
    FlatContinuousZeroCurve,
)


def test_reference_date_discount_factor_is_one() -> None:
    reference_date = date(2026, 9, 18)

    curve = FlatContinuousZeroCurve(
        reference_date=reference_date,
        rate=0.07,
    )

    assert curve.discount_factor(
        reference_date
    ) == pytest.approx(1.0)


def test_flat_curve_discount_factor() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=date(2026, 1, 1),
        rate=0.07,
    )

    target = date(2026, 12, 27)

    # Exactly 360 actual days.
    expected = exp(-0.07)

    assert curve.discount_factor(
        target
    ) == pytest.approx(expected)


def test_flat_curve_zero_rate() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=date(2026, 1, 1),
        rate=0.07,
    )

    assert curve.zero_rate(
        date(2026, 6, 1)
    ) == pytest.approx(0.07)


def test_flat_curve_forward_rate() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=date(2026, 1, 1),
        rate=0.07,
    )

    start = date(2026, 1, 1)
    end = date(2026, 1, 29)

    tau = 28 / 360

    expected = (
        exp(0.07 * tau) - 1
    ) / tau

    assert curve.forward_rate(
        start,
        end,
    ) == pytest.approx(expected)


def test_curve_rejects_date_before_reference() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=date(2026, 1, 2),
        rate=0.07,
    )

    with pytest.raises(
        ValueError,
        match="cannot precede",
    ):
        curve.discount_factor(
            date(2026, 1, 1)
        )