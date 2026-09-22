"""Report +1 bp one-factor F-TIIE quote perturbation diagnostics."""

from pathlib import Path

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.sensitivity import (
    analyze_quote_perturbations,
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


def print_summary(
    report,
) -> None:
    """Print one-row summary for every quote perturbation."""

    print(
        "F-TIIE +1 bp Quote Perturbation Diagnostics"
    )

    print(
        "=" * 115
    )

    print(
        f"Reference date : "
        f"{report.reference_date}"
    )

    print(
        f"Quote bump     : "
        f"{report.bump_bp:.4f} bp"
    )

    print(
        f"Forward period : "
        f"{report.forward_period_days} days"
    )

    print(
        f"Grid step      : "
        f"{report.grid_step_days} days"
    )

    print()

    print(
        f"{'Shock':>6} "
        f"{'Own ΔDF':>14} "
        f"{'Own ΔZero':>13} "
        f"{'Upstream ΔDF':>15} "
        f"{'Invariant':>11} "
        f"{'Fwd RMSE':>11} "
        f"{'Fwd Max':>11} "
        f"{'Max Date':>12}"
    )

    print(
        "-" * 115
    )

    for item in report.perturbations:
        print(
            f"{item.shock_tenor:>6} "
            f"{item.own_node_delta_df:>14.8f} "
            f"{item.own_node_zero_change_bp:>12.6f} "
            f"{item.maximum_upstream_abs_df_change:>15.3e} "
            f"{str(item.upstream_invariance_pass):>11} "
            f"{item.forward_summary.rmse_bp:>10.4f} "
            f"{item.forward_summary.max_abs_change_bp:>10.4f} "
            f"{str(item.forward_summary.max_abs_change_date):>12}"
        )

    print()


def print_zero_sensitivity_matrix(
    report,
) -> None:
    """Print node zero-rate response per bp of quote shock."""

    tenors = [
        sensitivity.node_tenor
        for sensitivity
        in report
        .perturbations[0]
        .node_sensitivities
    ]

    print(
        "Node Zero-Rate Sensitivity Matrix"
    )

    print(
        "(bp change in node zero rate "
        "per +1 bp quote shock)"
    )

    print()

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
                f"{sensitivity.zero_sensitivity_bp_per_bp:>9.4f}"
            )

        print(
            row
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

    report = analyze_quote_perturbations(
        quotes=quotes,
        calendar=calendar,
        bump_bp=1.0,
        forward_period_days=28,
        grid_step_days=7,
        upstream_df_tolerance=1e-12,
    )

    print_summary(
        report
    )

    print_zero_sensitivity_matrix(
        report
    )


if __name__ == "__main__":
    main()