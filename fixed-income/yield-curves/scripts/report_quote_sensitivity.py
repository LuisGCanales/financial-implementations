"""Report and persist +1 bp one-factor F-TIIE quote perturbation diagnostics.

The canonical F-TIIE bootstrap is recalibrated after independently
bumping each market quote by +1 bp.

The experiment measures:

    - own-node discount-factor response;
    - own-node zero-rate response;
    - upstream invariance of the sequential bootstrap;
    - dense 28-day forward-curve response;
    - node zero-rate sensitivity matrix.

Persistent outputs
------------------
Tables:
    reports/tables/05_quote_sensitivity/
        one_sided_quote_sensitivity_summary.csv
        one_sided_zero_sensitivity_matrix.csv

Text:
    reports/text/05_quote_sensitivity/
        one_sided_quote_sensitivity.txt
"""

from pathlib import Path

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
    save_matrix_csv,
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

REPORT_SECTION = (
    "05_quote_sensitivity"
)

QUOTE_BUMP_BP = 1.0
FORWARD_PERIOD_DAYS = 28
GRID_STEP_DAYS = 7
UPSTREAM_DF_TOLERANCE = 1e-12


def append_summary(
    *,
    text_report: TextReport,
    sensitivity_report,
) -> None:
    """Append one-row summary for every quote perturbation."""

    text_report.line(
        "F-TIIE +1 bp Quote Perturbation Diagnostics"
    )

    text_report.rule(
        character="=",
        width=115,
    )

    text_report.line()

    text_report.line(
        f"Reference date : "
        f"{sensitivity_report.reference_date}"
    )

    text_report.line(
        f"Quote bump     : "
        f"{sensitivity_report.bump_bp:.4f} bp"
    )

    text_report.line(
        f"Forward period : "
        f"{sensitivity_report.forward_period_days} days"
    )

    text_report.line(
        f"Grid step      : "
        f"{sensitivity_report.grid_step_days} days"
    )

    text_report.line(
        f"Shock count    : "
        f"{len(sensitivity_report.perturbations)}"
    )

    text_report.line()

    text_report.line(
        f"{'Shock':>6} "
        f"{'Own ΔDF':>14} "
        f"{'Own ΔZero':>13} "
        f"{'Upstream ΔDF':>15} "
        f"{'Invariant':>11} "
        f"{'Fwd RMSE':>11} "
        f"{'Fwd Max':>11} "
        f"{'Max Date':>12}"
    )

    text_report.rule(
        character="-",
        width=115,
    )

    for item in (
        sensitivity_report.perturbations
    ):
        text_report.line(
            f"{item.shock_tenor:>6} "
            f"{item.own_node_delta_df:>14.8f} "
            f"{item.own_node_zero_change_bp:>12.6f} "
            f"{item.maximum_upstream_abs_df_change:>15.3e} "
            f"{str(item.upstream_invariance_pass):>11} "
            f"{item.forward_summary.rmse_bp:>10.4f} "
            f"{item.forward_summary.max_abs_change_bp:>10.4f} "
            f"{str(item.forward_summary.max_abs_change_date):>12}"
        )

    text_report.line()


def append_zero_sensitivity_matrix(
    *,
    text_report: TextReport,
    sensitivity_report,
) -> None:
    """Append node zero-rate response per bp of quote shock."""

    if not sensitivity_report.perturbations:
        text_report.line(
            "Node Zero-Rate Sensitivity Matrix"
        )

        text_report.line(
            "No perturbation results available."
        )

        text_report.line()

        return

    tenors = [
        sensitivity.node_tenor
        for sensitivity
        in sensitivity_report
        .perturbations[0]
        .node_sensitivities
    ]

    text_report.line(
        "Node Zero-Rate Sensitivity Matrix"
    )

    text_report.line(
        "(bp change in node zero rate "
        "per +1 bp quote shock)"
    )

    text_report.line()

    header = (
        f"{'Shock':>6}"
        + "".join(
            f"{tenor:>9}"
            for tenor in tenors
        )
    )

    text_report.line(
        header
    )

    text_report.rule(
        character="-",
        width=len(
            header
        ),
    )

    for perturbation in (
        sensitivity_report.perturbations
    ):
        row = (
            f"{perturbation.shock_tenor:>6}"
        )

        for sensitivity in (
            perturbation.node_sensitivities
        ):
            row += (
                f"{sensitivity.zero_sensitivity_bp_per_bp:>9.4f}"
            )

        text_report.line(
            row
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

    sensitivity_report = (
        analyze_quote_perturbations(
            quotes=quotes,
            calendar=calendar,
            bump_bp=QUOTE_BUMP_BP,
            forward_period_days=(
                FORWARD_PERIOD_DAYS
            ),
            grid_step_days=(
                GRID_STEP_DAYS
            ),
            upstream_df_tolerance=(
                UPSTREAM_DF_TOLERANCE
            ),
        )
    )

    # --------------------------------------------------------------
    # Persist one-row summary per shocked quote.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="one_sided_quote_sensitivity_summary",
        header=(
            "reference_date",
            "shock_tenor",
            "quote_bump_bp",
            "own_node_delta_df",
            "own_node_zero_change_bp",
            "maximum_upstream_abs_df_change",
            "upstream_invariance_pass",
            "forward_period_days",
            "grid_step_days",
            "forward_rmse_bp",
            "forward_max_abs_change_bp",
            "forward_max_abs_change_date",
        ),
        rows=(
            (
                sensitivity_report
                .reference_date
                .isoformat(),
                item.shock_tenor,
                sensitivity_report.bump_bp,
                item.own_node_delta_df,
                item.own_node_zero_change_bp,
                item.maximum_upstream_abs_df_change,
                item.upstream_invariance_pass,
                sensitivity_report.forward_period_days,
                sensitivity_report.grid_step_days,
                item.forward_summary.rmse_bp,
                item.forward_summary.max_abs_change_bp,
                (
                    item.forward_summary
                    .max_abs_change_date
                    .isoformat()
                ),
            )
            for item
            in sensitivity_report.perturbations
        ),
    )

    # --------------------------------------------------------------
    # Persist node-zero sensitivity matrix.
    #
    # Rows:
    #     shocked market quote
    #
    # Columns:
    #     calibrated curve nodes
    #
    # Values:
    #     bp change in node zero rate per +1 bp quote shock
    # --------------------------------------------------------------

    if sensitivity_report.perturbations:
        node_tenors = [
            sensitivity.node_tenor
            for sensitivity
            in sensitivity_report
            .perturbations[0]
            .node_sensitivities
        ]

        shock_tenors = [
            perturbation.shock_tenor
            for perturbation
            in sensitivity_report.perturbations
        ]

        zero_sensitivity_matrix = [
            [
                sensitivity.zero_sensitivity_bp_per_bp
                for sensitivity
                in perturbation.node_sensitivities
            ]
            for perturbation
            in sensitivity_report.perturbations
        ]

        save_matrix_csv(
            section=REPORT_SECTION,
            stem="one_sided_zero_sensitivity_matrix",
            row_label_name="shock_tenor",
            row_labels=shock_tenors,
            column_labels=node_tenors,
            matrix=zero_sensitivity_matrix,
        )

    else:
        # Preserve an explicit artifact even if the analysis returns
        # no perturbation rows.
        save_csv(
            section=REPORT_SECTION,
            stem="one_sided_zero_sensitivity_matrix",
            header=(
                "shock_tenor",
            ),
            rows=(),
        )

    # --------------------------------------------------------------
    # Build human-readable report.
    # --------------------------------------------------------------

    text_report = TextReport()

    append_summary(
        text_report=text_report,
        sensitivity_report=(
            sensitivity_report
        ),
    )

    append_zero_sensitivity_matrix(
        text_report=text_report,
        sensitivity_report=(
            sensitivity_report
        ),
    )

    text_report.save(
        section=REPORT_SECTION,
        stem="one_sided_quote_sensitivity",
        echo=True,
    )


if __name__ == "__main__":
    main()