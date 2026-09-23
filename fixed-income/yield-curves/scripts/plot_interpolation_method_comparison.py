"""Visual comparison of F-TIIE interpolation methodologies.

Compares:

    1. Known synthetic truth
    2. Canonical log-linear discount-factor interpolation
    3. Linear continuously compounded zero-rate interpolation

All recovered curves are calibrated from the same frozen OIS quotes.
The true curve is introduced only after calibration for recovery
analysis.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve_with_method,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
    read_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


def act_360(
    start_date: date,
    end_date: date,
) -> float:
    """Return ACT/360 year fraction."""

    return (
        end_date
        - start_date
    ).days / 360.0


def build_date_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int = 7,
) -> tuple[date, ...]:
    """Build deterministic date grid including final date."""

    if step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    if end_date < start_date:
        raise ValueError(
            "End date cannot precede start date."
        )

    dates: list[date] = []

    current = start_date

    while current < end_date:
        dates.append(
            current
        )

        current += timedelta(
            days=step_days
        )

    if not dates or dates[-1] != end_date:
        dates.append(
            end_date
        )

    return tuple(
        dates
    )


def build_curves():
    """Calibrate both interpolation methods and build hidden truth."""

    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    log_linear_result = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LOG_LINEAR_DF
            ),
        )
    )

    linear_zero_result = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LINEAR_CONTINUOUS_ZERO
            ),
        )
    )

    log_linear_curve = (
        log_linear_result.curve
    )

    linear_zero_curve = (
        linear_zero_result.curve
    )

    if (
        log_linear_curve.reference_date
        != linear_zero_curve.reference_date
    ):
        raise RuntimeError(
            "Recovered curves have different "
            "reference dates."
        )

    if (
        log_linear_curve.node_dates
        != linear_zero_curve.node_dates
    ):
        raise RuntimeError(
            "Recovered curves have different "
            "pillar dates."
        )

    true_curve = (
        build_synthetic_known_truth_curve(
            log_linear_curve.reference_date
        )
    )

    return (
        log_linear_result,
        linear_zero_result,
        true_curve,
    )


def plot_discount_factors(
    *,
    log_linear_curve,
    linear_zero_curve,
    true_curve,
) -> None:
    """Compare recovered discount-factor functions."""

    reference_date = (
        log_linear_curve.reference_date
    )

    last_date = min(
        log_linear_curve.last_node_date,
        linear_zero_curve.last_node_date,
    )

    dates = build_date_grid(
        start_date=reference_date,
        end_date=last_date,
        step_days=7,
    )

    times = [
        act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    true_values = [
        true_curve.discount_factor(
            target_date
        )
        for target_date in dates
    ]

    log_linear_values = [
        log_linear_curve.discount_factor(
            target_date
        )
        for target_date in dates
    ]

    linear_zero_values = [
        linear_zero_curve.discount_factor(
            target_date
        )
        for target_date in dates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.2,
        label="True synthetic curve",
    )

    ax.plot(
        times,
        log_linear_values,
        linewidth=1.8,
        linestyle="--",
        label="Log-linear DF",
    )

    ax.plot(
        times,
        linear_zero_values,
        linewidth=1.8,
        linestyle=":",
        label="Linear continuous zero",
    )

    ax.set_title(
        "Discount-Factor Recovery by Interpolation Method"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Discount factor"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def plot_zero_rates(
    *,
    log_linear_curve,
    linear_zero_curve,
    true_curve,
) -> None:
    """Compare continuously compounded zero curves."""

    reference_date = (
        log_linear_curve.reference_date
    )

    last_date = min(
        log_linear_curve.last_node_date,
        linear_zero_curve.last_node_date,
    )

    dates = build_date_grid(
        start_date=(
            reference_date
            + timedelta(days=1)
        ),
        end_date=last_date,
        step_days=7,
    )

    times = [
        act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    true_values = [
        true_curve.zero_rate(
            target_date
        )
        * 100.0
        for target_date in dates
    ]

    log_linear_values = [
        log_linear_curve.zero_rate(
            target_date
        )
        * 100.0
        for target_date in dates
    ]

    linear_zero_values = [
        linear_zero_curve.zero_rate(
            target_date
        )
        * 100.0
        for target_date in dates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.2,
        label="True synthetic zero curve",
    )

    ax.plot(
        times,
        log_linear_values,
        linewidth=1.8,
        linestyle="--",
        label="Log-linear DF",
    )

    ax.plot(
        times,
        linear_zero_values,
        linewidth=1.8,
        linestyle=":",
        label="Linear continuous zero",
    )

    ax.set_title(
        "Zero-Rate Recovery by Interpolation Method"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Continuously compounded zero rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def plot_forward_rates(
    *,
    log_linear_curve,
    linear_zero_curve,
    true_curve,
    forward_days: int = 28,
) -> None:
    """Compare 28-day simple forward curves."""

    reference_date = (
        log_linear_curve.reference_date
    )

    last_date = min(
        log_linear_curve.last_node_date,
        linear_zero_curve.last_node_date,
    )

    last_start_date = (
        last_date
        - timedelta(
            days=forward_days
        )
    )

    start_dates = build_date_grid(
        start_date=reference_date,
        end_date=last_start_date,
        step_days=7,
    )

    times = [
        act_360(
            reference_date,
            start_date,
        )
        for start_date in start_dates
    ]

    true_values: list[float] = []
    log_linear_values: list[float] = []
    linear_zero_values: list[float] = []

    for start_date in start_dates:
        end_date = (
            start_date
            + timedelta(
                days=forward_days
            )
        )

        true_values.append(
            true_curve.forward_rate(
                start_date,
                end_date,
            )
            * 100.0
        )

        log_linear_values.append(
            log_linear_curve.forward_rate(
                start_date,
                end_date,
            )
            * 100.0
        )

        linear_zero_values.append(
            linear_zero_curve.forward_rate(
                start_date,
                end_date,
            )
            * 100.0
        )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.2,
        label="True synthetic 28D forward",
    )

    ax.plot(
        times,
        log_linear_values,
        linewidth=1.8,
        linestyle="--",
        label="Log-linear DF",
    )

    ax.plot(
        times,
        linear_zero_values,
        linewidth=1.8,
        linestyle=":",
        label="Linear continuous zero",
    )

    ax.set_title(
        "28-Day Forward Recovery by Interpolation Method"
    )

    ax.set_xlabel(
        "Forward start time from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "28-day simple forward rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def main() -> None:
    (
        log_linear_result,
        linear_zero_result,
        true_curve,
    ) = build_curves()

    log_linear_curve = (
        log_linear_result.curve
    )

    linear_zero_curve = (
        linear_zero_result.curve
    )

    plot_discount_factors(
        log_linear_curve=log_linear_curve,
        linear_zero_curve=linear_zero_curve,
        true_curve=true_curve,
    )

    plot_zero_rates(
        log_linear_curve=log_linear_curve,
        linear_zero_curve=linear_zero_curve,
        true_curve=true_curve,
    )

    plot_forward_rates(
        log_linear_curve=log_linear_curve,
        linear_zero_curve=linear_zero_curve,
        true_curve=true_curve,
        forward_days=28,
    )


if __name__ == "__main__":
    main()