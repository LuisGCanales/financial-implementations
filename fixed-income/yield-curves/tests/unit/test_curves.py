from datetime import date
from math import exp

import pytest

from yield_curves.curves import (
    CurveInterpolationMethod,
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


def test_curve_interpolation_method_contains_supported_values() -> None:
    assert tuple(
        method.value
        for method in CurveInterpolationMethod
    ) == (
        "LOG_LINEAR_DF",
        "LINEAR_CONTINUOUS_ZERO",
        "CUBIC_CONTINUOUS_ZERO",
        "PCHIP_CONTINUOUS_ZERO",
    )


@pytest.mark.parametrize("method, curve_class", (
    (CurveInterpolationMethod.LOG_LINEAR_DF, "LogLinearDiscountCurve"),
    (CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO, "LinearContinuousZeroCurve"),
    (CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO, "CubicContinuousZeroCurve"),
    (CurveInterpolationMethod.PCHIP_CONTINUOUS_ZERO, "PchipContinuousZeroCurve"),
))
def test_nodal_factory_preserves_representations(method, curve_class):
    import yield_curves.curves as curves

    arguments = dict(
        reference_date=date(2026, 1, 1),
        node_dates=(date(2026, 2, 1), date(2026, 4, 1), date(2026, 7, 1)),
        discount_factors=(0.993, 0.979, 0.958),
    )
    actual = curves.build_nodal_curve(method=method, **arguments)
    expected = getattr(curves, curve_class)(**arguments)
    assert type(actual) is type(expected)
    assert actual.node_dates == expected.node_dates
    assert actual.discount_factors == expected.discount_factors
    for day in (*actual.node_dates, date(2026, 3, 1), date(2026, 5, 1)):
        assert actual.discount_factor(day) == expected.discount_factor(day)
        assert actual.zero_rate(day) == expected.zero_rate(day)


def test_nodal_factory_rejects_unknown_method():
    from yield_curves.curves import build_nodal_curve

    with pytest.raises(ValueError, match="Unsupported interpolation method"):
        build_nodal_curve(method="UNKNOWN", reference_date=date(2026, 1, 1),
                          node_dates=(), discount_factors=())
