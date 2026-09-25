"""Compare and persist three F-TIIE interpolation methodologies.

All methods are calibrated with the same simultaneous nodal calibration
engine so that the interpolation rule is the primary experimental
difference.

Methods
-------
1. LOG_LINEAR_DF
2. LINEAR_CONTINUOUS_ZERO
3. CUBIC_CONTINUOUS_ZERO

The synthetic known-truth curve is introduced only after calibration
and is used exclusively for recovery analysis.

Persistent outputs
------------------
Tables:
    reports/tables/06_interpolation_comparison/
        three_method_global_recovery.csv
        three_method_recovery_by_horizon.csv
        simultaneous_calibration_diagnostics.csv

Text:
    reports/text/06_interpolation_comparison/
        three_method_interpolation_comparison.txt

Metadata:
    reports/metadata/06_interpolation_comparison/
        experiment_metadata.json
"""

from __future__ import annotations

from pathlib import Path

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
from yield_curves.recovery import (
    calculate_horizon_recovery_metrics,
    calculate_recovery_metrics,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
    save_json,
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

SCENARIO_NAME = (
    "FTIIE_KNOWN_TRUTH_V1"
)

CALIBRATION_ENGINE = (
    "simultaneous_nodal_least_squares"
)


METHODS = (
    CurveInterpolationMethod.LOG_LINEAR_DF,
    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
)


def append_global_comparison(
    *,
    text_report: TextReport,
    results,
) -> None:
    """Append global recovery comparison."""

    text_report.line(
        "F-TIIE Three-Method Interpolation Comparison"
    )

    text_report.rule(
        character="=",
        width=140,
    )

    text_report.line()

    text_report.line(
        f"{'Method':<28}"
        f"{'Success':>10}"
        f"{'Reprice Max':>15}"
        f"{'DF RMSE':>14}"
        f"{'Zero RMSE':>14}"
        f"{'Zero Max':>12}"
        f"{'Fwd RMSE':>14}"
        f"{'Fwd Max':>12}"
    )

    text_report.line(
        f"{'':<28}"
        f"{'':>10}"
        f"{'(bp)':>15}"
        f"{'(abs)':>14}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
    )

    text_report.rule(
        character="-",
        width=140,
    )

    for method in METHODS:
        (
            calibration,
            recovery,
            _,
        ) = results[
            method
        ]

        text_report.line(
            f"{method.value:<28}"
            f"{str(calibration.success):>10}"
            f"{calibration.max_abs_repricing_error_bp:>15.8f}"
            f"{recovery.dense_df_absolute.rmse:>14.8f}"
            f"{recovery.zero_rate_bp.rmse:>14.4f}"
            f"{recovery.zero_rate_bp.max_abs_error:>12.4f}"
            f"{recovery.forward_28d_bp.rmse:>14.4f}"
            f"{recovery.forward_28d_bp.max_abs_error:>12.4f}"
        )

    text_report.line()


def append_horizon_metric_table(
    *,
    text_report: TextReport,
    results,
    title: str,
    value_getter,
    decimals: int,
) -> None:
    """Append one maturity-horizon comparison table."""

    first_horizon_set = (
        results[
            METHODS[0]
        ][2]
    )

    horizon_names = [
        item.horizon.name
        for item in first_horizon_set
    ]

    header = (
        f"{'Method':<28}"
        + "".join(
            f"{name:>18}"
            for name in horizon_names
        )
    )

    text_report.line()

    text_report.line(
        title
    )

    text_report.line()

    text_report.line(
        header
    )

    text_report.rule(
        character="-",
        width=len(
            header
        ),
    )

    for method in METHODS:
        horizon_metrics = (
            results[
                method
            ][2]
        )

        row = (
            f"{method.value:<28}"
        )

        for item in horizon_metrics:
            value = (
                value_getter(
                    item
                )
            )

            row += (
                f"{value:>18.{decimals}f}"
            )

        text_report.line(
            row
        )

    text_report.line()


def append_calibration_diagnostics(
    *,
    text_report: TextReport,
    results,
) -> None:
    """Append simultaneous-calibration optimizer diagnostics."""

    text_report.line()

    text_report.line(
        "Simultaneous Calibration Diagnostics"
    )

    text_report.line()

    text_report.line(
        f"{'Method':<28}"
        f"{'nfev':>10}"
        f"{'njev':>10}"
        f"{'Cost':>16}"
        f"{'Optimality':>16}"
        f"{'RMSE Reprice':>16}"
    )

    text_report.line(
        f"{'':<28}"
        f"{'':>10}"
        f"{'':>10}"
        f"{'':>16}"
        f"{'':>16}"
        f"{'(bp)':>16}"
    )

    text_report.rule(
        character="-",
        width=96,
    )

    for method in METHODS:
        calibration = (
            results[
                method
            ][0]
        )

        njev = (
            "-"
            if (
                calibration
                .jacobian_evaluations
                is None
            )
            else str(
                calibration
                .jacobian_evaluations
            )
        )

        text_report.line(
            f"{method.value:<28}"
            f"{calibration.function_evaluations:>10}"
            f"{njev:>10}"
            f"{calibration.cost:>16.6e}"
            f"{calibration.optimality:>16.6e}"
            f"{calibration.rmse_repricing_error_bp:>16.8f}"
        )

    text_report.line()


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    results = {}

    reference_date = None

    for method in METHODS:
        calibration = (
            calibrate_ftiie_ois_curve_simultaneously(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
            )
        )

        if not calibration.success:
            raise RuntimeError(
                f"Calibration failed for "
                f"{method.value}: "
                f"{calibration.message}"
            )

        curve = (
            calibration.curve
        )

        if reference_date is None:
            reference_date = (
                curve.reference_date
            )

        elif (
            curve.reference_date
            != reference_date
        ):
            raise RuntimeError(
                "Interpolation methods produced "
                "different reference dates."
            )

        # IMPORTANT:
        # The synthetic truth enters only after calibration.
        true_curve = (
            build_synthetic_known_truth_curve(
                curve.reference_date
            )
        )

        recovery = (
            calculate_recovery_metrics(
                true_curve=true_curve,
                recovered_curve=curve,
                pillar_dates=(
                    curve.node_dates
                ),
                last_supported_date=(
                    curve.last_node_date
                ),
                dense_grid_step_days=(
                    DENSE_GRID_STEP_DAYS
                ),
                forward_period_days=(
                    FORWARD_PERIOD_DAYS
                ),
            )
        )

        horizon_recovery = (
            calculate_horizon_recovery_metrics(
                true_curve=true_curve,
                recovered_curve=curve,
                last_supported_date=(
                    curve.last_node_date
                ),
                dense_grid_step_days=(
                    DENSE_GRID_STEP_DAYS
                ),
                forward_period_days=(
                    FORWARD_PERIOD_DAYS
                ),
            )
        )

        results[
            method
        ] = (
            calibration,
            recovery,
            horizon_recovery,
        )

    assert reference_date is not None

    # --------------------------------------------------------------
    # Persist global recovery comparison.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="three_method_global_recovery",
        header=(
            "scenario",
            "reference_date",
            "method",
            "calibration_success",
            "max_repricing_error_bp",
            "repricing_rmse_bp",
            "dense_df_rmse",
            "dense_df_mae",
            "dense_df_max_abs_error",
            "zero_rmse_bp",
            "zero_mae_bp",
            "zero_max_abs_error_bp",
            "forward_28d_rmse_bp",
            "forward_28d_mae_bp",
            "forward_28d_max_abs_error_bp",
            "dense_grid_step_days",
            "forward_period_days",
        ),
        rows=(
            (
                SCENARIO_NAME,
                reference_date.isoformat(),
                method.value,
                calibration.success,
                calibration.max_abs_repricing_error_bp,
                calibration.rmse_repricing_error_bp,
                recovery.dense_df_absolute.rmse,
                recovery.dense_df_absolute.mae,
                recovery.dense_df_absolute.max_abs_error,
                recovery.zero_rate_bp.rmse,
                recovery.zero_rate_bp.mae,
                recovery.zero_rate_bp.max_abs_error,
                recovery.forward_28d_bp.rmse,
                recovery.forward_28d_bp.mae,
                recovery.forward_28d_bp.max_abs_error,
                recovery.dense_grid_step_days,
                recovery.forward_period_days,
            )
            for method in METHODS
            for (
                calibration,
                recovery,
                _,
            )
            in (
                results[
                    method
                ],
            )
        ),
    )

    # --------------------------------------------------------------
    # Persist horizon-segmented recovery comparison.
    #
    # Long format:
    # one row per interpolation method and maturity horizon.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="three_method_recovery_by_horizon",
        header=(
            "scenario",
            "reference_date",
            "method",
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
        rows=(
            (
                SCENARIO_NAME,
                reference_date.isoformat(),
                method.value,
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
            for method in METHODS
            for item in (
                results[
                    method
                ][2]
            )
        ),
    )

    # --------------------------------------------------------------
    # Persist optimizer/calibration diagnostics.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="simultaneous_calibration_diagnostics",
        header=(
            "scenario",
            "reference_date",
            "method",
            "success",
            "function_evaluations",
            "jacobian_evaluations",
            "cost",
            "optimality",
            "repricing_rmse_bp",
            "max_abs_repricing_error_bp",
            "optimizer_message",
        ),
        rows=(
            (
                SCENARIO_NAME,
                reference_date.isoformat(),
                method.value,
                calibration.success,
                calibration.function_evaluations,
                (
                    ""
                    if (
                        calibration
                        .jacobian_evaluations
                        is None
                    )
                    else (
                        calibration
                        .jacobian_evaluations
                    )
                ),
                calibration.cost,
                calibration.optimality,
                calibration.rmse_repricing_error_bp,
                calibration.max_abs_repricing_error_bp,
                calibration.message,
            )
            for method in METHODS
            for calibration in (
                results[
                    method
                ][0],
            )
        ),
    )

    # --------------------------------------------------------------
    # Persist experiment metadata.
    # --------------------------------------------------------------

    save_json(
        section=REPORT_SECTION,
        stem="experiment_metadata",
        data={
            "scenario": SCENARIO_NAME,
            "reference_date": (
                reference_date.isoformat()
            ),
            "quote_source": (
                "data/synthetic/"
                "ftiie_ois_quotes_v1.csv"
            ),
            "calibration_engine": (
                CALIBRATION_ENGINE
            ),
            "interpolation_methods": [
                method.value
                for method in METHODS
            ],
            "dense_grid_step_days": (
                DENSE_GRID_STEP_DAYS
            ),
            "forward_period_days": (
                FORWARD_PERIOD_DAYS
            ),
            "known_truth_usage": (
                "Introduced only after calibration "
                "for recovery analysis."
            ),
            "global_recovery_output": (
                "reports/tables/"
                "06_interpolation_comparison/"
                "three_method_global_recovery.csv"
            ),
            "horizon_recovery_output": (
                "reports/tables/"
                "06_interpolation_comparison/"
                "three_method_recovery_by_horizon.csv"
            ),
            "calibration_diagnostics_output": (
                "reports/tables/"
                "06_interpolation_comparison/"
                "simultaneous_calibration_diagnostics.csv"
            ),
        },
    )

    # --------------------------------------------------------------
    # Build human-readable report.
    # --------------------------------------------------------------

    text_report = (
        TextReport()
    )

    append_global_comparison(
        text_report=text_report,
        results=results,
    )

    append_horizon_metric_table(
        text_report=text_report,
        results=results,
        title=(
            "Zero-Rate Recovery RMSE (bp)"
        ),
        value_getter=lambda item: (
            item.zero_rate_bp.rmse
        ),
        decimals=4,
    )

    append_horizon_metric_table(
        text_report=text_report,
        results=results,
        title=(
            "28-Day Forward Recovery RMSE (bp)"
        ),
        value_getter=lambda item: (
            item.forward_28d_bp.rmse
        ),
        decimals=4,
    )

    append_horizon_metric_table(
        text_report=text_report,
        results=results,
        title=(
            "28-Day Forward Maximum Absolute Error (bp)"
        ),
        value_getter=lambda item: (
            item.forward_28d_bp
            .max_abs_error
        ),
        decimals=4,
    )

    append_horizon_metric_table(
        text_report=text_report,
        results=results,
        title=(
            "Dense Discount-Factor RMSE"
        ),
        value_getter=lambda item: (
            item.dense_df_absolute.rmse
        ),
        decimals=8,
    )

    append_calibration_diagnostics(
        text_report=text_report,
        results=results,
    )

    text_report.save(
        section=REPORT_SECTION,
        stem=(
            "three_method_interpolation_comparison"
        ),
        echo=True,
    )


if __name__ == "__main__":
    main()