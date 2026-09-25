"""Report quantitative recovery metrics for the synthetic bootstrap.

The canonical synthetic F-TIIE curve is bootstrapped from frozen OIS
quotes and compared with the hidden known-truth curve only after
calibration.

Persistent outputs
------------------
Tables:
    reports/tables/02_bootstrap_recovery/
        recovery_metrics_global.csv
        recovery_metrics_by_horizon.csv

Text:
    reports/text/02_bootstrap_recovery/
        bootstrap_recovery_metrics.txt
"""

from pathlib import Path

from yield_curves.project_paths import find_project_root
from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.recovery import (
    ErrorSummary,
    calculate_horizon_recovery_metrics,
    calculate_recovery_metrics,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
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
    "02_bootstrap_recovery"
)

DENSE_GRID_STEP_DAYS = 7
FORWARD_PERIOD_DAYS = 28


def append_metric(
    *,
    report: TextReport,
    title: str,
    metric: ErrorSummary,
    unit: str,
    decimals: int = 6,
) -> None:
    """Append one metric family to a human-readable report."""

    report.line(
        title
    )

    report.line(
        f"  observations : "
        f"{metric.observation_count}"
    )

    report.line(
        f"  bias         : "
        f"{metric.bias:.{decimals}f} {unit}"
    )

    report.line(
        f"  MAE          : "
        f"{metric.mae:.{decimals}f} {unit}"
    )

    report.line(
        f"  RMSE         : "
        f"{metric.rmse:.{decimals}f} {unit}"
    )

    report.line(
        f"  max abs error: "
        f"{metric.max_abs_error:.{decimals}f} {unit}"
    )

    report.line(
        f"  max error at : "
        f"{metric.max_abs_error_date}"
    )

    report.line()


def append_horizon_metrics_table(
    *,
    report: TextReport,
    horizon_metrics,
) -> None:
    """Append compact recovery comparison by maturity horizon."""

    report.line(
        "Recovery Metrics by Horizon"
    )

    report.line()

    header = (
        f"{'Horizon':<18}"
        f"{'DF RMSE':>12}"
        f"{'DF RMSE':>14}"
        f"{'Zero RMSE':>14}"
        f"{'Zero Max':>12}"
        f"{'Fwd RMSE':>14}"
        f"{'Fwd Max':>12}"
    )

    units = (
        f"{'':<18}"
        f"{'(abs)':>12}"
        f"{'(ppm)':>14}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
    )

    report.line(
        header
    )

    report.line(
        units
    )

    report.rule(
        character="-",
        width=len(
            header
        ),
    )

    for item in horizon_metrics:
        report.line(
            f"{item.horizon.name:<18}"
            f"{item.dense_df_absolute.rmse:>12.8f}"
            f"{item.dense_df_relative_ppm.rmse:>14.3f}"
            f"{item.zero_rate_bp.rmse:>14.4f}"
            f"{item.zero_rate_bp.max_abs_error:>12.4f}"
            f"{item.forward_28d_bp.rmse:>14.4f}"
            f"{item.forward_28d_bp.max_abs_error:>12.4f}"
        )

    report.line()


def build_global_metric_rows(
    *,
    reference_date,
    interpolation_method: str,
    metrics,
):
    """Build long-format rows for global recovery metrics."""

    metric_families = (
        (
            "pillar_df_absolute",
            "DF",
            metrics.pillar_df_absolute,
        ),
        (
            "pillar_df_relative",
            "ppm",
            metrics.pillar_df_relative_ppm,
        ),
        (
            "dense_df_absolute",
            "DF",
            metrics.dense_df_absolute,
        ),
        (
            "dense_df_relative",
            "ppm",
            metrics.dense_df_relative_ppm,
        ),
        (
            "continuous_zero_rate",
            "bp",
            metrics.zero_rate_bp,
        ),
        (
            "forward_28d",
            "bp",
            metrics.forward_28d_bp,
        ),
    )

    return tuple(
        (
            reference_date.isoformat(),
            interpolation_method,
            metric_name,
            unit,
            metric.observation_count,
            metric.bias,
            metric.mae,
            metric.rmse,
            metric.max_abs_error,
            metric.max_abs_error_date.isoformat(),
            metrics.dense_grid_step_days,
            metrics.forward_period_days,
        )
        for (
            metric_name,
            unit,
            metric,
        )
        in metric_families
    )


def build_horizon_metric_rows(
    *,
    reference_date,
    interpolation_method: str,
    horizon_metrics,
):
    """Build one machine-readable row per maturity horizon."""

    return tuple(
        (
            reference_date.isoformat(),
            interpolation_method,
            item.horizon.name,
            item.dense_df_absolute.observation_count,
            item.dense_df_absolute.bias,
            item.dense_df_absolute.mae,
            item.dense_df_absolute.rmse,
            item.dense_df_absolute.max_abs_error,
            item.dense_df_relative_ppm.bias,
            item.dense_df_relative_ppm.mae,
            item.dense_df_relative_ppm.rmse,
            item.dense_df_relative_ppm.max_abs_error,
            item.zero_rate_bp.observation_count,
            item.zero_rate_bp.bias,
            item.zero_rate_bp.mae,
            item.zero_rate_bp.rmse,
            item.zero_rate_bp.max_abs_error,
            item.forward_28d_bp.observation_count,
            item.forward_28d_bp.bias,
            item.forward_28d_bp.mae,
            item.forward_28d_bp.rmse,
            item.forward_28d_bp.max_abs_error,
        )
        for item in horizon_metrics
    )


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

    reference_date = (
        recovered_curve.reference_date
    )

    interpolation_method = (
        bootstrap_result
        .interpolation_method
        .value
    )

    # IMPORTANT:
    # True curve is introduced only after calibration.
    true_curve = (
        build_synthetic_known_truth_curve(
            reference_date
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
        dense_grid_step_days=(
            DENSE_GRID_STEP_DAYS
        ),
        forward_period_days=(
            FORWARD_PERIOD_DAYS
        ),
    )

    horizon_metrics = (
        calculate_horizon_recovery_metrics(
            true_curve=true_curve,
            recovered_curve=recovered_curve,
            last_supported_date=(
                recovered_curve.last_node_date
            ),
            dense_grid_step_days=(
                DENSE_GRID_STEP_DAYS
            ),
            forward_period_days=(
                FORWARD_PERIOD_DAYS
            ),
        )
    )

    # --------------------------------------------------------------
    # Persist global recovery metrics.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="recovery_metrics_global",
        header=(
            "reference_date",
            "interpolation_method",
            "metric",
            "unit",
            "observation_count",
            "bias",
            "mae",
            "rmse",
            "max_abs_error",
            "max_abs_error_date",
            "dense_grid_step_days",
            "forward_period_days",
        ),
        rows=build_global_metric_rows(
            reference_date=reference_date,
            interpolation_method=(
                interpolation_method
            ),
            metrics=metrics,
        ),
    )

    # --------------------------------------------------------------
    # Persist horizon-segmented recovery metrics.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="recovery_metrics_by_horizon",
        header=(
            "reference_date",
            "interpolation_method",
            "horizon",
            "df_abs_observation_count",
            "df_abs_bias",
            "df_abs_mae",
            "df_abs_rmse",
            "df_abs_max_error",
            "df_relative_bias_ppm",
            "df_relative_mae_ppm",
            "df_relative_rmse_ppm",
            "df_relative_max_error_ppm",
            "zero_observation_count",
            "zero_bias_bp",
            "zero_mae_bp",
            "zero_rmse_bp",
            "zero_max_error_bp",
            "forward_observation_count",
            "forward_bias_bp",
            "forward_mae_bp",
            "forward_rmse_bp",
            "forward_max_error_bp",
        ),
        rows=build_horizon_metric_rows(
            reference_date=reference_date,
            interpolation_method=(
                interpolation_method
            ),
            horizon_metrics=(
                horizon_metrics
            ),
        ),
    )

    # --------------------------------------------------------------
    # Build human-readable report.
    # --------------------------------------------------------------

    report = TextReport()

    report.line(
        "Synthetic F-TIIE Curve Recovery Metrics"
    )

    report.rule(
        character="=",
        width=100,
    )

    report.line()

    report.line(
        f"Reference date       : "
        f"{reference_date}"
    )

    report.line(
        f"Interpolation method : "
        f"{interpolation_method}"
    )

    report.line(
        f"Dense grid           : "
        f"{metrics.dense_grid_step_days} days"
    )

    report.line(
        f"Forward period       : "
        f"{metrics.forward_period_days} days"
    )

    report.line(
        f"Calibration pillars  : "
        f"{len(pillar_dates)}"
    )

    report.line()

    report.rule(
        character="=",
        width=60,
    )

    report.line()

    append_metric(
        report=report,
        title="Pillar DF Absolute Error",
        metric=(
            metrics.pillar_df_absolute
        ),
        unit="DF",
        decimals=8,
    )

    append_metric(
        report=report,
        title="Pillar DF Relative Error",
        metric=(
            metrics.pillar_df_relative_ppm
        ),
        unit="ppm",
        decimals=3,
    )

    append_metric(
        report=report,
        title="Dense-Grid DF Absolute Error",
        metric=(
            metrics.dense_df_absolute
        ),
        unit="DF",
        decimals=8,
    )

    append_metric(
        report=report,
        title="Dense-Grid DF Relative Error",
        metric=(
            metrics.dense_df_relative_ppm
        ),
        unit="ppm",
        decimals=3,
    )

    append_metric(
        report=report,
        title="Continuous Zero-Rate Error",
        metric=(
            metrics.zero_rate_bp
        ),
        unit="bp",
        decimals=4,
    )

    append_metric(
        report=report,
        title="28-Day Forward-Rate Error",
        metric=(
            metrics.forward_28d_bp
        ),
        unit="bp",
        decimals=4,
    )

    report.rule(
        character="=",
        width=100,
    )

    report.line()

    append_horizon_metrics_table(
        report=report,
        horizon_metrics=(
            horizon_metrics
        ),
    )

    report.save(
        section=REPORT_SECTION,
        stem="bootstrap_recovery_metrics",
        echo=True,
    )


if __name__ == "__main__":
    main()