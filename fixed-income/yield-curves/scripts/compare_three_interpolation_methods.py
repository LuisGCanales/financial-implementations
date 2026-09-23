"""Compare three F-TIIE interpolation methodologies.

All methods are calibrated with the same simultaneous nodal calibration
engine so that the interpolation rule is the primary experimental
difference.

Methods
-------
1. LOG_LINEAR_DF
2. LINEAR_CONTINUOUS_ZERO
3. CUBIC_CONTINUOUS_ZERO
"""

from __future__ import annotations

from pathlib import Path

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


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    results = {}

    for method in METHODS:
        calibration = (
            calibrate_ftiie_ois_curve_simultaneously(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
            )
        )

        curve = calibration.curve

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
                dense_grid_step_days=7,
                forward_period_days=28,
            )
        )

        horizon_recovery = (
            calculate_horizon_recovery_metrics(
                true_curve=true_curve,
                recovered_curve=curve,
                last_supported_date=(
                    curve.last_node_date
                ),
                dense_grid_step_days=7,
                forward_period_days=28,
            )
        )

        results[method] = (
            calibration,
            recovery,
            horizon_recovery,
        )

    # ==============================================================
    # Global comparison
    # ==============================================================

    print(
        "F-TIIE Three-Method Interpolation Comparison"
    )

    print(
        "=" * 140
    )

    print()

    print(
        f"{'Method':<28}"
        f"{'Success':>10}"
        f"{'Reprice Max':>15}"
        f"{'DF RMSE':>14}"
        f"{'Zero RMSE':>14}"
        f"{'Zero Max':>12}"
        f"{'Fwd RMSE':>14}"
        f"{'Fwd Max':>12}"
    )

    print(
        f"{'':<28}"
        f"{'':>10}"
        f"{'(bp)':>15}"
        f"{'(abs)':>14}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
    )

    print(
        "-" * 140
    )

    for method in METHODS:
        (
            calibration,
            recovery,
            _,
        ) = results[method]

        print(
            f"{method.value:<28}"
            f"{str(calibration.success):>10}"
            f"{calibration.max_abs_repricing_error_bp:>15.8f}"
            f"{recovery.dense_df_absolute.rmse:>14.8f}"
            f"{recovery.zero_rate_bp.rmse:>14.4f}"
            f"{recovery.zero_rate_bp.max_abs_error:>12.4f}"
            f"{recovery.forward_28d_bp.rmse:>14.4f}"
            f"{recovery.forward_28d_bp.max_abs_error:>12.4f}"
        )

    # ==============================================================
    # Horizon names
    # ==============================================================

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

    # ==============================================================
    # Zero recovery
    # ==============================================================

    print()
    print()
    print(
        "Zero-Rate Recovery RMSE (bp)"
    )

    print()

    print(header)

    print(
        "-" * len(header)
    )

    for method in METHODS:
        horizon_metrics = (
            results[method][2]
        )

        row = (
            f"{method.value:<28}"
        )

        for item in horizon_metrics:
            row += (
                f"{item.zero_rate_bp.rmse:>18.4f}"
            )

        print(row)

    # ==============================================================
    # Forward recovery
    # ==============================================================

    print()
    print()
    print(
        "28-Day Forward Recovery RMSE (bp)"
    )

    print()

    print(header)

    print(
        "-" * len(header)
    )

    for method in METHODS:
        horizon_metrics = (
            results[method][2]
        )

        row = (
            f"{method.value:<28}"
        )

        for item in horizon_metrics:
            row += (
                f"{item.forward_28d_bp.rmse:>18.4f}"
            )

        print(row)

    # ==============================================================
    # Forward max error
    # ==============================================================

    print()
    print()
    print(
        "28-Day Forward Maximum Absolute Error (bp)"
    )

    print()

    print(header)

    print(
        "-" * len(header)
    )

    for method in METHODS:
        horizon_metrics = (
            results[method][2]
        )

        row = (
            f"{method.value:<28}"
        )

        for item in horizon_metrics:
            row += (
                f"{item.forward_28d_bp.max_abs_error:>18.4f}"
            )

        print(row)

    # ==============================================================
    # Dense DF recovery
    # ==============================================================

    print()
    print()
    print(
        "Dense Discount-Factor RMSE"
    )

    print()

    print(header)

    print(
        "-" * len(header)
    )

    for method in METHODS:
        horizon_metrics = (
            results[method][2]
        )

        row = (
            f"{method.value:<28}"
        )

        for item in horizon_metrics:
            row += (
                f"{item.dense_df_absolute.rmse:>18.8f}"
            )

        print(row)

    # ==============================================================
    # Optimizer diagnostics
    # ==============================================================

    print()
    print()
    print(
        "Simultaneous Calibration Diagnostics"
    )

    print()

    print(
        f"{'Method':<28}"
        f"{'nfev':>10}"
        f"{'njev':>10}"
        f"{'Cost':>16}"
        f"{'Optimality':>16}"
        f"{'RMSE Reprice':>16}"
    )

    print(
        f"{'':<28}"
        f"{'':>10}"
        f"{'':>10}"
        f"{'':>16}"
        f"{'':>16}"
        f"{'(bp)':>16}"
    )

    print(
        "-" * 96
    )

    for method in METHODS:
        calibration = (
            results[method][0]
        )

        njev = (
            "-"
            if calibration.jacobian_evaluations
            is None
            else str(
                calibration
                .jacobian_evaluations
            )
        )

        print(
            f"{method.value:<28}"
            f"{calibration.function_evaluations:>10}"
            f"{njev:>10}"
            f"{calibration.cost:>16.6e}"
            f"{calibration.optimality:>16.6e}"
            f"{calibration.rmse_repricing_error_bp:>16.8f}"
        )


if __name__ == "__main__":
    main()