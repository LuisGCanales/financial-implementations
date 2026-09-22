"""Report symmetric quote-perturbation diagnostics."""

from pathlib import Path

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.sensitivity import (
    analyze_central_quote_perturbations,
)
from yield_curves.synthetic import (
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

    report = (
        analyze_central_quote_perturbations(
            quotes=quotes,
            calendar=calendar,
            bump_bp=1.0,
            forward_period_days=28,
            grid_step_days=7,
        )
    )

    print(
        "F-TIIE Symmetric Quote Perturbation Diagnostics"
    )

    print(
        "=" * 118
    )

    print(
        f"Reference date : "
        f"{report.reference_date}"
    )

    print(
        f"Symmetric bump : "
        f"+/- {report.bump_bp:.4f} bp"
    )

    print()

    print(
        f"{'Shock':>6} "
        f"{'Own dZ/dK':>12} "
        f"{'Own Curv':>12} "
        f"{'Fwd Sens RMSE':>15} "
        f"{'Fwd Sens Max':>14} "
        f"{'Fwd Curv RMSE':>15} "
        f"{'Fwd Curv Max':>14} "
        f"{'Max Sens Date':>14}"
    )

    print(
        "-" * 118
    )

    for item in report.perturbations:
        forward = (
            item.forward_summary
        )

        print(
            f"{item.shock_tenor:>6} "
            f"{item.own_node_sensitivity:>12.6f} "
            f"{item.own_node_curvature:>12.6f} "
            f"{forward.sensitivity_rmse:>15.6f} "
            f"{forward.max_abs_sensitivity:>14.6f} "
            f"{forward.curvature_rmse:>15.6f} "
            f"{forward.max_abs_curvature:>14.6f} "
            f"{str(forward.max_abs_sensitivity_date):>14}"
        )

    print()
    print(
        "Central Node Zero-Rate Sensitivity Matrix"
    )

    print(
        "(bp node-zero change per bp quote shock)"
    )

    print()

    tenors = [
        item.node_tenor
        for item in (
            report
            .perturbations[0]
            .node_sensitivities
        )
    ]

    header = (
        f"{'Shock':>6}"
        + "".join(
            f"{tenor:>9}"
            for tenor in tenors
        )
    )

    print(
        header
    )

    print(
        "-" * len(header)
    )

    for perturbation in (
        report.perturbations
    ):
        row = (
            f"{perturbation.shock_tenor:>6}"
        )

        for sensitivity in (
            perturbation
            .node_sensitivities
        ):
            row += (
                f"{sensitivity.central_sensitivity_bp_per_bp:>9.4f}"
            )

        print(
            row
        )

    print()
    print(
        "Own-Node Local Curvature"
    )

    print(
        "(bp node-zero curvature per quote-bp squared)"
    )

    print()

    for item in report.perturbations:
        print(
            f"{item.shock_tenor:>6}: "
            f"{item.own_node_curvature: .8f}"
        )


if __name__ == "__main__":
    main()