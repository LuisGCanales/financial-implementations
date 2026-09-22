from datetime import date

import pytest

from yield_curves.curves import (
    LogLinearDiscountCurve,
)
from yield_curves.recovery import (
    build_standard_recovery_horizons,
    calculate_horizon_recovery_metrics,
)
from yield_curves.tenors import (
    add_calendar_months,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)


NODE_DATES = (
    add_calendar_months(
        REFERENCE_DATE,
        12,
    ),
    add_calendar_months(
        REFERENCE_DATE,
        60,
    ),
    add_calendar_months(
        REFERENCE_DATE,
        120,
    ),
    add_calendar_months(
        REFERENCE_DATE,
        360,
    ),
)


TRUE_DFS = (
    0.93,
    0.70,
    0.49,
    0.12,
)


def build_true_curve():
    return LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=NODE_DATES,
        discount_factors=TRUE_DFS,
    )


def test_standard_horizon_names() -> None:
    horizons = (
        build_standard_recovery_horizons(
            reference_date=REFERENCE_DATE,
            last_supported_date=NODE_DATES[-1],
        )
    )

    assert tuple(
        horizon.name
        for horizon in horizons
    ) == (
        "0-1Y",
        "1-5Y",
        "5-10Y",
        "10Y-curve-end",
    )


def test_standard_horizons_are_contiguous() -> None:
    horizons = (
        build_standard_recovery_horizons(
            reference_date=REFERENCE_DATE,
            last_supported_date=NODE_DATES[-1],
        )
    )

    for earlier, later in zip(
        horizons,
        horizons[1:],
    ):
        assert (
            earlier.end_date
            == later.start_date
        )


def test_identical_curves_have_zero_error_in_every_horizon() -> None:
    true_curve = build_true_curve()

    recovered_curve = build_true_curve()

    metrics = (
        calculate_horizon_recovery_metrics(
            true_curve=true_curve,
            recovered_curve=recovered_curve,
            last_supported_date=(
                NODE_DATES[-1]
            ),
            dense_grid_step_days=7,
            forward_period_days=28,
        )
    )

    assert len(metrics) == 4

    for horizon in metrics:
        assert (
            horizon
            .dense_df_absolute
            .rmse
            == pytest.approx(0.0)
        )

        assert (
            horizon
            .dense_df_relative_ppm
            .rmse
            == pytest.approx(0.0)
        )

        assert (
            horizon
            .zero_rate_bp
            .rmse
            == pytest.approx(0.0)
        )

        assert (
            horizon
            .forward_28d_bp
            .rmse
            == pytest.approx(0.0)
        )


def test_perturbed_curve_produces_segmented_errors() -> None:
    true_curve = build_true_curve()

    recovered_curve = (
        LogLinearDiscountCurve(
            reference_date=REFERENCE_DATE,
            node_dates=NODE_DATES,
            discount_factors=(
                0.929,
                0.702,
                0.488,
                0.121,
            ),
        )
    )

    metrics = (
        calculate_horizon_recovery_metrics(
            true_curve=true_curve,
            recovered_curve=recovered_curve,
            last_supported_date=(
                NODE_DATES[-1]
            ),
            dense_grid_step_days=7,
            forward_period_days=28,
        )
    )

    assert all(
        item.dense_df_absolute.rmse > 0
        for item in metrics
    )

    assert all(
        item.zero_rate_bp.rmse > 0
        for item in metrics
    )

    assert all(
        item.forward_28d_bp.rmse > 0
        for item in metrics
    )


def test_final_horizon_includes_last_curve_date() -> None:
    horizons = (
        build_standard_recovery_horizons(
            reference_date=REFERENCE_DATE,
            last_supported_date=NODE_DATES[-1],
        )
    )

    final_horizon = horizons[-1]

    assert final_horizon.contains(
        NODE_DATES[-1]
    )


def test_boundary_date_belongs_to_later_bucket() -> None:
    horizons = (
        build_standard_recovery_horizons(
            reference_date=REFERENCE_DATE,
            last_supported_date=NODE_DATES[-1],
        )
    )

    one_year = add_calendar_months(
        REFERENCE_DATE,
        12,
    )

    assert not horizons[0].contains(
        one_year
    )

    assert horizons[1].contains(
        one_year
    )