"""Visual recovery comparison for three interpolation methods."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.calibration import (
    calibrate_ftiie_ois_curve_simultaneously,
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


METHODS = (
    CurveInterpolationMethod.LOG_LINEAR_DF,
    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
)


LABELS = {
    CurveInterpolationMethod.LOG_LINEAR_DF:
        "Log-linear DF",

    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO:
        "Linear continuous zero",

    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO:
        "Cubic continuous zero",
}


LINESTYLES = {
    CurveInterpolationMethod.LOG_LINEAR_DF:
        "--",

    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO:
        ":",

    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO:
        "-.",
}


def act_360(
    start_date: date,
    end_date: date,
) -> float:
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
    if step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
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


def calibrate_curves():
    """Calibrate all methods from the same quote set."""

    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    curves = {}

    for method in METHODS:
        result = (
            calibrate_ftiie_ois_curve_simultaneously(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
            )
        )

        if not result.success:
            raise RuntimeError(
                f"Calibration failed for "
                f"{method.value}: "
                f"{result.message}"
            )

        curves[method] = (
            result.curve
        )

    reference_date = (
        curves[
            METHODS[0]
        ].reference_date
    )

    true_curve = (
        build_synthetic_known_truth_curve(
            reference_date
        )
    )

    return (
        curves,
        true_curve,
    )


def plot_discount_factors(
    *,
    curves,
    true_curve,
) -> None:
    reference_date = (
        true_curve.reference_date
    )

    last_date = min(
        curve.last_node_date
        for curve in curves.values()
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

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.4,
        label="True synthetic curve",
    )

    for method in METHODS:
        curve = curves[method]

        values = [
            curve.discount_factor(
                target_date
            )
            for target_date in dates
        ]

        ax.plot(
            times,
            values,
            linewidth=1.8,
            linestyle=(
                LINESTYLES[
                    method
                ]
            ),
            label=(
                LABELS[
                    method
                ]
            ),
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
    curves,
    true_curve,
) -> None:
    reference_date = (
        true_curve.reference_date
    )

    last_date = min(
        curve.last_node_date
        for curve in curves.values()
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

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.4,
        label="True synthetic zero curve",
    )

    for method in METHODS:
        curve = curves[method]

        values = [
            curve.zero_rate(
                target_date
            )
            * 100.0
            for target_date in dates
        ]

        ax.plot(
            times,
            values,
            linewidth=1.8,
            linestyle=(
                LINESTYLES[
                    method
                ]
            ),
            label=(
                LABELS[
                    method
                ]
            ),
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
    curves,
    true_curve,
    forward_days: int = 28,
) -> None:
    reference_date = (
        true_curve.reference_date
    )

    last_date = min(
        curve.last_node_date
        for curve in curves.values()
    )

    last_start_date = (
        last_date
        - timedelta(
            days=forward_days
        )
    )

    start_dates = (
        build_date_grid(
            start_date=reference_date,
            end_date=last_start_date,
            step_days=7,
        )
    )

    times = [
        act_360(
            reference_date,
            start_date,
        )
        for start_date in start_dates
    ]

    true_values: list[float] = []

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

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values,
        linewidth=2.4,
        label="True synthetic 28D forward",
    )

    for method in METHODS:
        curve = curves[method]

        values: list[float] = []

        for start_date in start_dates:
            end_date = (
                start_date
                + timedelta(
                    days=forward_days
                )
            )

            values.append(
                curve.forward_rate(
                    start_date,
                    end_date,
                )
                * 100.0
            )

        ax.plot(
            times,
            values,
            linewidth=1.8,
            linestyle=(
                LINESTYLES[
                    method
                ]
            ),
            label=(
                LABELS[
                    method
                ]
            ),
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



def plot_cubic_instantaneous_forward(
    *,
    curves,
    true_curve,
) -> None:
    """Inspect smooth instantaneous-forward behavior of cubic zero."""

    cubic_curve = curves[
        CurveInterpolationMethod
        .CUBIC_CONTINUOUS_ZERO
    ]

    reference_date = (
        cubic_curve.reference_date
    )

    dates = build_date_grid(
        start_date=(
            reference_date
            + timedelta(days=1)
        ),
        end_date=(
            cubic_curve.last_node_date
        ),
        step_days=7,
    )

    times = [
        act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    cubic_forwards = [
        cubic_curve
        .instantaneous_forward_rate(
            target_date
        )
        * 100.0
        for target_date in dates
    ]

    # Numerical approximation to the true instantaneous forward:
    # use a one-day simple forward as a very short-horizon proxy.
    true_forwards = []

    for target_date in dates:
        next_date = (
            target_date
            + timedelta(days=1)
        )

        if (
            next_date
            > cubic_curve.last_node_date
        ):
            break

        true_forwards.append(
            true_curve.forward_rate(
                target_date,
                next_date,
            )
            * 100.0
        )

    usable_count = len(
        true_forwards
    )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times[:usable_count],
        true_forwards,
        linewidth=2.2,
        label="True 1D forward proxy",
    )

    ax.plot(
        times[:usable_count],
        cubic_forwards[:usable_count],
        linewidth=1.8,
        linestyle="-.",
        label="Cubic-zero instantaneous forward",
    )

    ax.set_title(
        "Cubic-Zero Instantaneous Forward Diagnostic"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Forward rate (%)"
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
        curves,
        true_curve,
    ) = calibrate_curves()

    plot_discount_factors(
        curves=curves,
        true_curve=true_curve,
    )

    plot_zero_rates(
        curves=curves,
        true_curve=true_curve,
    )

    plot_forward_rates(
        curves=curves,
        true_curve=true_curve,
        forward_days=28,
    )

    plot_cubic_instantaneous_forward(
        curves=curves,
        true_curve=true_curve,
    )

if __name__ == "__main__":
    main()