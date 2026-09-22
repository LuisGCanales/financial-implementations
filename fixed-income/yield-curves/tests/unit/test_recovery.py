from datetime import date

import pytest

from yield_curves.curves import (
    LogLinearDiscountCurve,
)
from yield_curves.recovery import (
    calculate_recovery_metrics,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)

NODE_DATES = (
    date(2026, 4, 1),
    date(2026, 7, 1),
    date(2027, 1, 1),
)

DISCOUNT_FACTORS = (
    0.98,
    0.96,
    0.92,
)


def build_reference_curve():
    return LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=NODE_DATES,
        discount_factors=DISCOUNT_FACTORS,
    )


def test_identical_curves_have_zero_recovery_error() -> None:
    true_curve = build_reference_curve()
    recovered_curve = build_reference_curve()

    metrics = calculate_recovery_metrics(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
        pillar_dates=NODE_DATES,
        last_supported_date=NODE_DATES[-1],
        dense_grid_step_days=7,
        forward_period_days=28,
    )

    assert (
        metrics.pillar_df_absolute.rmse
        == pytest.approx(0.0)
    )

    assert (
        metrics.dense_df_absolute.rmse
        == pytest.approx(0.0)
    )

    assert (
        metrics.zero_rate_bp.rmse
        == pytest.approx(0.0)
    )

    assert (
        metrics.forward_28d_bp.rmse
        == pytest.approx(0.0)
    )


def test_perturbed_curve_produces_nonzero_errors() -> None:
    true_curve = build_reference_curve()

    recovered_curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=NODE_DATES,
        discount_factors=(
            0.979,
            0.961,
            0.918,
        ),
    )

    metrics = calculate_recovery_metrics(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
        pillar_dates=NODE_DATES,
        last_supported_date=NODE_DATES[-1],
        dense_grid_step_days=7,
        forward_period_days=28,
    )

    assert (
        metrics.pillar_df_absolute.rmse
        > 0
    )

    assert (
        metrics.zero_rate_bp.rmse
        > 0
    )

    assert (
        metrics.forward_28d_bp.rmse
        > 0
    )


def test_relative_df_error_is_reported_in_ppm() -> None:
    true_curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.90,
        ),
    )

    recovered_curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.90009,
        ),
    )

    metrics = calculate_recovery_metrics(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
        pillar_dates=(
            date(2027, 1, 1),
        ),
        last_supported_date=(
            date(2027, 1, 1)
        ),
    )

    # (0.90009 / 0.90 - 1) * 1e6 = 100 ppm
    assert (
        metrics
        .pillar_df_relative_ppm
        .max_abs_error
        == pytest.approx(100.0)
    )


def test_reference_dates_must_match() -> None:
    true_curve = build_reference_curve()

    recovered_curve = (
        LogLinearDiscountCurve(
            reference_date=date(
                2026,
                1,
                2,
            ),
            node_dates=NODE_DATES,
            discount_factors=DISCOUNT_FACTORS,
        )
    )

    with pytest.raises(
        ValueError,
        match="same reference date",
    ):
        calculate_recovery_metrics(
            true_curve=true_curve,
            recovered_curve=recovered_curve,
            pillar_dates=NODE_DATES,
            last_supported_date=NODE_DATES[-1],
        )