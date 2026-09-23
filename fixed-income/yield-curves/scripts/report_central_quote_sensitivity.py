"""Report and persist symmetric quote-perturbation diagnostics.

Each F-TIIE OIS calibration quote is independently perturbed by
+/- 1 bp and the curve is recalibrated under both shocks.

The experiment measures:

    - central own-node zero-rate sensitivity;
    - own-node local curvature;
    - central node zero-rate sensitivity matrix;
    - dense 28-day forward sensitivity;
    - dense 28-day forward curvature.

Persistent outputs
------------------
Tables:
    reports/tables/05_quote_sensitivity/
        central_quote_sensitivity_summary.csv
        central_zero_sensitivity_matrix.csv
        own_node_local_curvature.csv

Text:
    reports/text/05_quote_sensitivity/
        central_quote_sensitivity.txt
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

REPORT_SECTION = (
    "05_quote_sensitivity"
)

QUOTE_BUMP_BP = 1.0
FORWARD_PERIOD_DAYS = 28
GRID_STEP_DAYS = 7


def append_summary(
    *,
    text_report: TextReport,
    sensitivity_report,
) -> None:
    """Append symmetric quote-perturbation summary."""

    text_report.line(
        "F-TIIE Symmetric Quote Perturbation Diagnostics"
    )

    text_report.rule(
        character="=",
        width=118,
    )

    text_report.line()

    text_report.line(
        f"Reference date : "
        f"{sensitivity_report.reference_date}"
    )

    text_report.line(
        f"Symmetric bump : "
        f"+/- {sensitivity_report.bump_bp:.4f} bp"
    )

    text_report.line(
        f"Forward period : "
        f"{FORWARD_PERIOD_DAYS} days"
    )

    text_report.line(
        f"Grid step      : "
        f"{GRID_STEP_DAYS} days"
    )

    text_report.line(
        f"Shock count    : "
        f"{len(sensitivity_report.perturbations)}"
    )

    text_report.line()

    text_report.line(
        f"{'Shock':>6} "
        f"{'Own dZ/dK':>12} "
        f"{'Own Curv':>12} "
        f"{'Fwd Sens RMSE':>15} "
        f"{'Fwd Sens Max':>14} "
        f"{'Fwd Curv RMSE':>15} "
        f"{'Fwd Curv Max':>14} "
        f"{'Max Sens Date':>14}"
    )

    text_report.rule(
        character="-",
        width=118,
    )

    for item in (
        sensitivity_report.perturbations
    ):
        forward = (
            item.forward_summary
        )

        text_report.line(
            f"{item.shock_tenor:>6} "
            f"{item.own_node_sensitivity:>12.6f} "
            f"{item.own_node_curvature:>12.6f} "
            f"{forward.sensitivity_rmse:>15.6f} "
            f"{forward.max_abs_sensitivity:>14.6f} "
            f"{forward.curvature_rmse:>15.6f} "
            f"{forward.max_abs_curvature:>14.6f} "
            f"{str(forward.max_abs_sensitivity_date):>14}"
        )

    text_report.line()


def append_zero_sensitivity_matrix(
    *,
    text_report: TextReport,
    sensitivity_report,
) -> None:
    """Append central node zero-rate sensitivity matrix."""

    text_report.line(
        "Central Node Zero-Rate Sensitivity Matrix"
    )

    text_report.line(
        "(bp node-zero change per bp quote shock)"
    )

    text_report.line()

    if not sensitivity_report.perturbations:
        text_report.line(
            "No perturbation results available."
        )

        text_report.line()

        return

    tenors = [
        item.node_tenor
        for item in (
            sensitivity_report
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
                f"{sensitivity.central_sensitivity_bp_per_bp:>9.4f}"
            )

        text_report.line(
            row
        )

    text_report.line()


def append_own_node_curvature(
    *,
    text_report: TextReport,
    sensitivity_report,
) -> None:
    """Append own-node local curvature diagnostics."""

    text_report.line(
        "Own-Node Local Curvature"
    )

    text_report.line(
        "(bp node-zero curvature per quote-bp squared)"
    )

    text_report.line()

    if not sensitivity_report.perturbations:
        text_report.line(
            "No perturbation results available."
        )

        text_report.line()

        return

    for item in (
        sensitivity_report.perturbations
    ):
        text_report.line(
            f"{item.shock_tenor:>6}: "
            f"{item.own_node_curvature: .8f}"
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
        analyze_central_quote_perturbations(
            quotes=quotes,
            calendar=calendar,
            bump_bp=QUOTE_BUMP_BP,
            forward_period_days=(
                FORWARD_PERIOD_DAYS
            ),
            grid_step_days=(
                GRID_STEP_DAYS
            ),
        )
    )

    # --------------------------------------------------------------
    # Persist one-row summary per shocked quote.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="central_quote_sensitivity_summary",
        header=(
            "reference_date",
            "shock_tenor",
            "symmetric_bump_bp",
            "own_node_sensitivity_bp_per_bp",
            "own_node_curvature_bp_per_bp2",
            "forward_period_days",
            "grid_step_days",
            "forward_sensitivity_rmse",
            "forward_max_abs_sensitivity",
            "forward_max_abs_sensitivity_date",
            "forward_curvature_rmse",
            "forward_max_abs_curvature",
        ),
        rows=(
            (
                sensitivity_report
                .reference_date
                .isoformat(),
                item.shock_tenor,
                sensitivity_report.bump_bp,
                item.own_node_sensitivity,
                item.own_node_curvature,
                FORWARD_PERIOD_DAYS,
                GRID_STEP_DAYS,
                (
                    item.forward_summary
                    .sensitivity_rmse
                ),
                (
                    item.forward_summary
                    .max_abs_sensitivity
                ),
                (
                    item.forward_summary
                    .max_abs_sensitivity_date
                    .isoformat()
                ),
                (
                    item.forward_summary
                    .curvature_rmse
                ),
                (
                    item.forward_summary
                    .max_abs_curvature
                ),
            )
            for item
            in sensitivity_report.perturbations
        ),
    )

    # --------------------------------------------------------------
    # Persist central node-zero sensitivity matrix.
    #
    # Rows:
    #     shocked market quote
    #
    # Columns:
    #     calibrated curve nodes
    #
    # Values:
    #     central bp change in node zero rate
    #     per 1 bp market-quote shock
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
                sensitivity
                .central_sensitivity_bp_per_bp
                for sensitivity
                in perturbation.node_sensitivities
            ]
            for perturbation
            in sensitivity_report.perturbations
        ]

        save_matrix_csv(
            section=REPORT_SECTION,
            stem="central_zero_sensitivity_matrix",
            row_label_name="shock_tenor",
            row_labels=shock_tenors,
            column_labels=node_tenors,
            matrix=zero_sensitivity_matrix,
        )

    else:
        save_csv(
            section=REPORT_SECTION,
            stem="central_zero_sensitivity_matrix",
            header=(
                "shock_tenor",
            ),
            rows=(),
        )

    # --------------------------------------------------------------
    # Persist own-node curvature separately.
    #
    # This makes the local-linearity diagnostic easy to consume
    # independently from the larger sensitivity summary.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="own_node_local_curvature",
        header=(
            "reference_date",
            "shock_tenor",
            "symmetric_bump_bp",
            "own_node_sensitivity_bp_per_bp",
            "own_node_curvature_bp_per_bp2",
        ),
        rows=(
            (
                sensitivity_report
                .reference_date
                .isoformat(),
                item.shock_tenor,
                sensitivity_report.bump_bp,
                item.own_node_sensitivity,
                item.own_node_curvature,
            )
            for item
            in sensitivity_report.perturbations
        ),
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

    append_own_node_curvature(
        text_report=text_report,
        sensitivity_report=(
            sensitivity_report
        ),
    )

    text_report.save(
        section=REPORT_SECTION,
        stem="central_quote_sensitivity",
        echo=True,
    )


if __name__ == "__main__":
    main()