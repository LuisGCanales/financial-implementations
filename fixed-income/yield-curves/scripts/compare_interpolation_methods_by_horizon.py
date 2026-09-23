"""Compare interpolation-method recovery by maturity horizon."""

from pathlib import Path

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
    calculate_horizon_recovery_metrics,
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


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    methods = (
        CurveInterpolationMethod.LOG_LINEAR_DF,
        CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    )

    results = {}

    for method in methods:
        bootstrap_result = (
            bootstrap_ftiie_ois_curve_with_method(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
            )
        )

        recovered_curve = (
            bootstrap_result.curve
        )

        true_curve = (
            build_synthetic_known_truth_curve(
                recovered_curve.reference_date
            )
        )

        metrics = (
            calculate_horizon_recovery_metrics(
                true_curve=true_curve,
                recovered_curve=recovered_curve,
                last_supported_date=(
                    recovered_curve.last_node_date
                ),
                dense_grid_step_days=7,
                forward_period_days=28,
            )
        )

        results[method] = metrics

    print(
        "Interpolation Recovery by Horizon"
    )

    print(
        "=" * 130
    )

    print()

    print(
        "Zero-Rate Recovery RMSE (bp)"
    )

    print()

    horizon_names = [
        item.horizon.name
        for item in next(
            iter(
                results.values()
            )
        )
    ]

    header = (
        f"{'Method':<28}"
        + "".join(
            f"{name:>18}"
            for name in horizon_names
        )
    )

    print(header)
    print(
        "-" * len(header)
    )

    for method, metrics in results.items():
        row = (
            f"{method.value:<28}"
        )

        for item in metrics:
            row += (
                f"{item.zero_rate_bp.rmse:>18.4f}"
            )

        print(row)

    print()
    print(
        "28-Day Forward Recovery RMSE (bp)"
    )

    print()

    print(header)
    print(
        "-" * len(header)
    )

    for method, metrics in results.items():
        row = (
            f"{method.value:<28}"
        )

        for item in metrics:
            row += (
                f"{item.forward_28d_bp.rmse:>18.4f}"
            )

        print(row)

    print()
    print(
        "28-Day Forward Maximum Absolute Error (bp)"
    )

    print()

    print(header)
    print(
        "-" * len(header)
    )

    for method, metrics in results.items():
        row = (
            f"{method.value:<28}"
        )

        for item in metrics:
            row += (
                f"{item.forward_28d_bp.max_abs_error:>18.4f}"
            )

        print(row)

    print()
    print(
        "Dense Discount-Factor RMSE"
    )

    print()

    print(header)
    print(
        "-" * len(header)
    )

    for method, metrics in results.items():
        row = (
            f"{method.value:<28}"
        )

        for item in metrics:
            row += (
                f"{item.dense_df_absolute.rmse:>18.8f}"
            )

        print(row)


if __name__ == "__main__":
    main()