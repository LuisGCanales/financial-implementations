"""Compare canonical and challenger interpolation methodologies."""

from pathlib import Path

from yield_curves.project_paths import find_project_root
from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve_with_method,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.recovery import (
    calculate_recovery_metrics,
)
from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
    read_synthetic_ois_quotes_csv,
)
from yield_curves.validation import (
    validate_bootstrap_result,
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


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    methods = (
        CurveInterpolationMethod
        .LOG_LINEAR_DF,

        CurveInterpolationMethod
        .LINEAR_CONTINUOUS_ZERO,
    )

    print(
        "F-TIIE Interpolation Method Comparison"
    )

    print(
        "=" * 124
    )

    print()

    print(
        f"{'Method':<26}"
        f"{'Status':>10}"
        f"{'Reprice Max':>15}"
        f"{'DF RMSE':>14}"
        f"{'Zero RMSE':>14}"
        f"{'Zero Max':>12}"
        f"{'Fwd RMSE':>14}"
        f"{'Fwd Max':>12}"
    )

    print(
        f"{'':<26}"
        f"{'':>10}"
        f"{'(bp)':>15}"
        f"{'(abs)':>14}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
        f"{'(bp)':>14}"
        f"{'(bp)':>12}"
    )

    print(
        "-" * 124
    )

    for method in methods:
        result = (
            bootstrap_ftiie_ois_curve_with_method(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
            )
        )

        validation = (
            validate_bootstrap_result(
                bootstrap_result=result,
                quotes=quotes,
                calendar=calendar,
            )
        )

        true_curve = (
            build_synthetic_known_truth_curve(
                result.curve.reference_date
            )
        )

        recovery = (
            calculate_recovery_metrics(
                true_curve=true_curve,
                recovered_curve=(
                    result.curve
                ),
                pillar_dates=tuple(
                    step.pillar_date
                    for step
                    in result.steps
                ),
                last_supported_date=(
                    result
                    .curve
                    .last_node_date
                ),
                dense_grid_step_days=7,
                forward_period_days=28,
            )
        )

        print(
            f"{method.value:<26}"
            f"{validation.status:>10}"
            f"{validation.max_abs_repricing_error_bp:>15.8f}"
            f"{recovery.dense_df_absolute.rmse:>14.8f}"
            f"{recovery.zero_rate_bp.rmse:>14.4f}"
            f"{recovery.zero_rate_bp.max_abs_error:>12.4f}"
            f"{recovery.forward_28d_bp.rmse:>14.4f}"
            f"{recovery.forward_28d_bp.max_abs_error:>12.4f}"
        )


if __name__ == "__main__":
    main()