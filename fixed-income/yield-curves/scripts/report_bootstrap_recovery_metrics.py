"""Report quantitative recovery metrics for the synthetic bootstrap."""

from pathlib import Path

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.recovery import (
    ErrorSummary,
    calculate_recovery_metrics,
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


def print_metric(
    *,
    title: str,
    metric: ErrorSummary,
    unit: str,
    decimals: int = 6,
) -> None:
    """Print one metric family."""

    print(title)

    print(
        f"  observations : "
        f"{metric.observation_count}"
    )

    print(
        f"  bias         : "
        f"{metric.bias:.{decimals}f} {unit}"
    )

    print(
        f"  MAE          : "
        f"{metric.mae:.{decimals}f} {unit}"
    )

    print(
        f"  RMSE         : "
        f"{metric.rmse:.{decimals}f} {unit}"
    )

    print(
        f"  max abs error: "
        f"{metric.max_abs_error:.{decimals}f} {unit}"
    )

    print(
        f"  max error at : "
        f"{metric.max_abs_error_date}"
    )

    print()


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    bootstrap_result = (
        bootstrap_ftiie_ois_curve(
            quotes=quotes,
            calendar=calendar,
        )
    )

    recovered_curve = (
        bootstrap_result.curve
    )

    # True curve is introduced only after calibration.
    true_curve = (
        build_synthetic_known_truth_curve(
            recovered_curve.reference_date
        )
    )

    pillar_dates = tuple(
        step.pillar_date
        for step in bootstrap_result.steps
    )

    metrics = calculate_recovery_metrics(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
        pillar_dates=pillar_dates,
        last_supported_date=(
            recovered_curve.last_node_date
        ),
        dense_grid_step_days=7,
        forward_period_days=28,
    )

    print(
        "Synthetic F-TIIE Curve Recovery Metrics"
    )

    print(
        f"Reference date : "
        f"{recovered_curve.reference_date}"
    )

    print(
        f"Dense grid     : "
        f"{metrics.dense_grid_step_days} days"
    )

    print(
        f"Forward period : "
        f"{metrics.forward_period_days} days"
    )

    print()
    print(
        "=" * 60
    )
    print()

    print_metric(
        title="Pillar DF Absolute Error",
        metric=metrics.pillar_df_absolute,
        unit="DF",
        decimals=8,
    )

    print_metric(
        title="Pillar DF Relative Error",
        metric=metrics.pillar_df_relative_ppm,
        unit="ppm",
        decimals=3,
    )

    print_metric(
        title="Dense-Grid DF Absolute Error",
        metric=metrics.dense_df_absolute,
        unit="DF",
        decimals=8,
    )

    print_metric(
        title="Dense-Grid DF Relative Error",
        metric=metrics.dense_df_relative_ppm,
        unit="ppm",
        decimals=3,
    )

    print_metric(
        title="Continuous Zero-Rate Error",
        metric=metrics.zero_rate_bp,
        unit="bp",
        decimals=4,
    )

    print_metric(
        title="28-Day Forward-Rate Error",
        metric=metrics.forward_28d_bp,
        unit="bp",
        decimals=4,
    )


if __name__ == "__main__":
    main()