"""Visual recovery comparison for three interpolation methods.

All three curve representations are calibrated from the same frozen
synthetic F-TIIE OIS quote set using simultaneous nodal calibration.

Methods
-------
1. LOG_LINEAR_DF
2. LINEAR_CONTINUOUS_ZERO
3. CUBIC_CONTINUOUS_ZERO

The synthetic known-truth curve is introduced only after calibration
for recovery analysis.

Persistent outputs
------------------
Figures:
    reports/figures/06_interpolation_comparison/
        discount_factor_recovery_three_methods.png
        discount_factor_recovery_three_methods.svg
        zero_rate_recovery_three_methods.png
        zero_rate_recovery_three_methods.svg
        forward_28d_recovery_three_methods.png
        forward_28d_recovery_three_methods.svg
        cubic_zero_instantaneous_forward.png
        cubic_zero_instantaneous_forward.svg

Tables:
    reports/tables/06_interpolation_comparison/
        calibrated_nodes_three_methods.csv
        discount_factor_recovery_three_methods_dense.csv
        zero_rate_recovery_three_methods_dense.csv
        forward_28d_recovery_three_methods_dense.csv
        cubic_zero_instantaneous_forward_dense.csv

Rates are persisted in raw decimal form.
Percentage conversion is used only for plotting.

The dense CSV outputs make it possible to recreate the figures later
without rerunning the simultaneous calibrations.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.project_paths import find_project_root
from yield_curves.calibration import (
    calibrate_ftiie_ois_curve_simultaneously,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.reporting import (
    save_csv,
    save_figure,
)
from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
    read_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = (
    find_project_root(Path(__file__))
)

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)

REPORT_SECTION = (
    "06_interpolation_comparison"
)

DENSE_GRID_STEP_DAYS = 7
FORWARD_PERIOD_DAYS = 28


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
    """Return ACT/360 year fraction."""

    return (
        end_date
        - start_date
    ).days / 360.0


def build_date_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int = DENSE_GRID_STEP_DAYS,
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


def calibrate_curves():
    """Calibrate all methods from the same quote set.

    The calibrated node values are persisted because simultaneous
    calibration is relatively expensive and should not need to be
    repeated merely to inspect its numerical output.
    """

    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    calibration_results = {}
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

        calibration_results[
            method
        ] = result

        curves[
            method
        ] = result.curve

    reference_dates = {
        curve.reference_date
        for curve in curves.values()
    }

    if len(
        reference_dates
    ) != 1:
        raise RuntimeError(
            "Recovered curves have different "
            "reference dates."
        )

    node_date_sets = {
        curve.node_dates
        for curve in curves.values()
    }

    if len(
        node_date_sets
    ) != 1:
        raise RuntimeError(
            "Recovered curves have different "
            "pillar dates."
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

    # --------------------------------------------------------------
    # Persist calibrated nodal states.
    # --------------------------------------------------------------

    node_dates = (
        curves[
            METHODS[0]
        ].node_dates
    )

    log_linear_dfs = (
        curves[
            CurveInterpolationMethod
            .LOG_LINEAR_DF
        ].discount_factors
    )

    linear_zero_dfs = (
        curves[
            CurveInterpolationMethod
            .LINEAR_CONTINUOUS_ZERO
        ].discount_factors
    )

    cubic_zero_dfs = (
        curves[
            CurveInterpolationMethod
            .CUBIC_CONTINUOUS_ZERO
        ].discount_factors
    )

    save_csv(
        section=REPORT_SECTION,
        stem="calibrated_nodes_three_methods",
        header=(
            "node_date",
            "act360_years",
            "log_linear_discount_factor",
            "linear_continuous_zero_discount_factor",
            "cubic_continuous_zero_discount_factor",
            "log_linear_zero_rate",
            "linear_continuous_zero_rate",
            "cubic_continuous_zero_rate",
        ),
        rows=(
            (
                node_date.isoformat(),
                act_360(
                    reference_date,
                    node_date,
                ),
                log_linear_dfs[index],
                linear_zero_dfs[index],
                cubic_zero_dfs[index],
                curves[
                    CurveInterpolationMethod
                    .LOG_LINEAR_DF
                ].zero_rate(
                    node_date
                ),
                curves[
                    CurveInterpolationMethod
                    .LINEAR_CONTINUOUS_ZERO
                ].zero_rate(
                    node_date
                ),
                curves[
                    CurveInterpolationMethod
                    .CUBIC_CONTINUOUS_ZERO
                ].zero_rate(
                    node_date
                ),
            )
            for index, node_date
            in enumerate(
                node_dates
            )
        ),
    )

    return (
        calibration_results,
        curves,
        true_curve,
    )


def plot_discount_factors(
    *,
    curves,
    true_curve,
) -> None:
    """Plot and persist discount-factor recovery."""

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
        step_days=DENSE_GRID_STEP_DAYS,
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

    method_values = {
        method: [
            curves[
                method
            ].discount_factor(
                target_date
            )
            for target_date in dates
        ]
        for method in METHODS
    }

    # --------------------------------------------------------------
    # Persist dense numerical series.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem=(
            "discount_factor_recovery_"
            "three_methods_dense"
        ),
        header=(
            "date",
            "act360_years",
            "true_discount_factor",
            "log_linear_discount_factor",
            "linear_continuous_zero_discount_factor",
            "cubic_continuous_zero_discount_factor",
            "log_linear_error",
            "linear_continuous_zero_error",
            "cubic_continuous_zero_error",
        ),
        rows=(
            (
                target_date.isoformat(),
                times[index],
                true_values[index],
                method_values[
                    CurveInterpolationMethod
                    .LOG_LINEAR_DF
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .LINEAR_CONTINUOUS_ZERO
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .CUBIC_CONTINUOUS_ZERO
                ][index],
                (
                    method_values[
                        CurveInterpolationMethod
                        .LOG_LINEAR_DF
                    ][index]
                    - true_values[index]
                ),
                (
                    method_values[
                        CurveInterpolationMethod
                        .LINEAR_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                ),
                (
                    method_values[
                        CurveInterpolationMethod
                        .CUBIC_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                ),
            )
            for index, target_date
            in enumerate(
                dates
            )
        ),
    )

    # --------------------------------------------------------------
    # Plot.
    # --------------------------------------------------------------

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
        ax.plot(
            times,
            method_values[
                method
            ],
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="discount_factor_recovery_three_methods",
    )

    plt.show()


def plot_zero_rates(
    *,
    curves,
    true_curve,
) -> None:
    """Plot and persist continuously compounded zero-rate recovery."""

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
            + timedelta(
                days=1
            )
        ),
        end_date=last_date,
        step_days=DENSE_GRID_STEP_DAYS,
    )

    times = [
        act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    # Raw decimal rates are persisted.
    true_values = [
        true_curve.zero_rate(
            target_date
        )
        for target_date in dates
    ]

    method_values = {
        method: [
            curves[
                method
            ].zero_rate(
                target_date
            )
            for target_date in dates
        ]
        for method in METHODS
    }

    # --------------------------------------------------------------
    # Persist dense zero-rate recovery.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem=(
            "zero_rate_recovery_"
            "three_methods_dense"
        ),
        header=(
            "date",
            "act360_years",
            "true_zero_rate",
            "log_linear_zero_rate",
            "linear_continuous_zero_rate",
            "cubic_continuous_zero_rate",
            "log_linear_error_bp",
            "linear_continuous_zero_error_bp",
            "cubic_continuous_zero_error_bp",
        ),
        rows=(
            (
                target_date.isoformat(),
                times[index],
                true_values[index],
                method_values[
                    CurveInterpolationMethod
                    .LOG_LINEAR_DF
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .LINEAR_CONTINUOUS_ZERO
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .CUBIC_CONTINUOUS_ZERO
                ][index],
                (
                    method_values[
                        CurveInterpolationMethod
                        .LOG_LINEAR_DF
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
                (
                    method_values[
                        CurveInterpolationMethod
                        .LINEAR_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
                (
                    method_values[
                        CurveInterpolationMethod
                        .CUBIC_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
            )
            for index, target_date
            in enumerate(
                dates
            )
        ),
    )

    # --------------------------------------------------------------
    # Percentage conversion only for display.
    # --------------------------------------------------------------

    true_values_pct = [
        value * 100.0
        for value in true_values
    ]

    method_values_pct = {
        method: [
            value * 100.0
            for value in method_values[
                method
            ]
        ]
        for method in METHODS
    }

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values_pct,
        linewidth=2.4,
        label="True synthetic zero curve",
    )

    for method in METHODS:
        ax.plot(
            times,
            method_values_pct[
                method
            ],
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="zero_rate_recovery_three_methods",
    )

    plt.show()


def plot_forward_rates(
    *,
    curves,
    true_curve,
    forward_days: int = FORWARD_PERIOD_DAYS,
) -> None:
    """Plot and persist 28-day simple-forward recovery."""

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
            step_days=DENSE_GRID_STEP_DAYS,
        )
    )

    times = [
        act_360(
            reference_date,
            start_date,
        )
        for start_date in start_dates
    ]

    end_dates = [
        start_date
        + timedelta(
            days=forward_days
        )
        for start_date in start_dates
    ]

    true_values = [
        true_curve.forward_rate(
            start_date,
            end_date,
        )
        for start_date, end_date
        in zip(
            start_dates,
            end_dates,
        )
    ]

    method_values = {
        method: [
            curves[
                method
            ].forward_rate(
                start_date,
                end_date,
            )
            for start_date, end_date
            in zip(
                start_dates,
                end_dates,
            )
        ]
        for method in METHODS
    }

    # --------------------------------------------------------------
    # Persist raw decimal forward rates.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem=(
            "forward_28d_recovery_"
            "three_methods_dense"
        ),
        header=(
            "start_date",
            "end_date",
            "start_act360_years",
            "forward_period_days",
            "true_forward_rate",
            "log_linear_forward_rate",
            "linear_continuous_zero_forward_rate",
            "cubic_continuous_zero_forward_rate",
            "log_linear_error_bp",
            "linear_continuous_zero_error_bp",
            "cubic_continuous_zero_error_bp",
        ),
        rows=(
            (
                start_dates[
                    index
                ].isoformat(),
                end_dates[
                    index
                ].isoformat(),
                times[index],
                forward_days,
                true_values[index],
                method_values[
                    CurveInterpolationMethod
                    .LOG_LINEAR_DF
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .LINEAR_CONTINUOUS_ZERO
                ][index],
                method_values[
                    CurveInterpolationMethod
                    .CUBIC_CONTINUOUS_ZERO
                ][index],
                (
                    method_values[
                        CurveInterpolationMethod
                        .LOG_LINEAR_DF
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
                (
                    method_values[
                        CurveInterpolationMethod
                        .LINEAR_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
                (
                    method_values[
                        CurveInterpolationMethod
                        .CUBIC_CONTINUOUS_ZERO
                    ][index]
                    - true_values[index]
                )
                * 10_000.0,
            )
            for index in range(
                len(
                    start_dates
                )
            )
        ),
    )

    # --------------------------------------------------------------
    # Percentage conversion only for plotting.
    # --------------------------------------------------------------

    true_values_pct = [
        value * 100.0
        for value in true_values
    ]

    method_values_pct = {
        method: [
            value * 100.0
            for value in method_values[
                method
            ]
        ]
        for method in METHODS
    }

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_values_pct,
        linewidth=2.4,
        label="True synthetic 28D forward",
    )

    for method in METHODS:
        ax.plot(
            times,
            method_values_pct[
                method
            ],
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="forward_28d_recovery_three_methods",
    )

    plt.show()


def plot_cubic_instantaneous_forward(
    *,
    curves,
    true_curve,
) -> None:
    """Inspect and persist cubic-zero instantaneous-forward behavior.

    The true comparison series is currently a one-day simple-forward
    proxy rather than an analytical instantaneous forward.
    """

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
            + timedelta(
                days=1
            )
        ),
        end_date=(
            cubic_curve.last_node_date
        ),
        step_days=DENSE_GRID_STEP_DAYS,
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
        for target_date in dates
    ]

    # Numerical approximation to the true instantaneous forward:
    # use a one-day simple forward as a very short-horizon proxy.
    true_forwards: list[float] = []
    true_end_dates: list[date] = []

    for target_date in dates:
        next_date = (
            target_date
            + timedelta(
                days=1
            )
        )

        if (
            next_date
            > cubic_curve.last_node_date
        ):
            break

        true_end_dates.append(
            next_date
        )

        true_forwards.append(
            true_curve.forward_rate(
                target_date,
                next_date,
            )
        )

    usable_count = len(
        true_forwards
    )

    usable_dates = (
        dates[
            :usable_count
        ]
    )

    usable_times = (
        times[
            :usable_count
        ]
    )

    usable_cubic_forwards = (
        cubic_forwards[
            :usable_count
        ]
    )

    # --------------------------------------------------------------
    # Persist raw rates.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem=(
            "cubic_zero_instantaneous_"
            "forward_dense"
        ),
        header=(
            "date",
            "true_proxy_end_date",
            "act360_years",
            "true_1d_forward_proxy",
            "cubic_instantaneous_forward",
            "difference_bp",
        ),
        rows=(
            (
                usable_dates[
                    index
                ].isoformat(),
                true_end_dates[
                    index
                ].isoformat(),
                usable_times[index],
                true_forwards[index],
                usable_cubic_forwards[
                    index
                ],
                (
                    usable_cubic_forwards[
                        index
                    ]
                    - true_forwards[index]
                )
                * 10_000.0,
            )
            for index in range(
                usable_count
            )
        ),
    )

    # --------------------------------------------------------------
    # Percentage conversion only for presentation.
    # --------------------------------------------------------------

    true_forwards_pct = [
        value * 100.0
        for value in true_forwards
    ]

    cubic_forwards_pct = [
        value * 100.0
        for value in usable_cubic_forwards
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        usable_times,
        true_forwards_pct,
        linewidth=2.2,
        label="True 1D forward proxy",
    )

    ax.plot(
        usable_times,
        cubic_forwards_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="cubic_zero_instantaneous_forward",
    )

    plt.show()


def main() -> None:
    (
        _,
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
        forward_days=FORWARD_PERIOD_DAYS,
    )

    plot_cubic_instantaneous_forward(
        curves=curves,
        true_curve=true_curve,
    )


if __name__ == "__main__":
    main()