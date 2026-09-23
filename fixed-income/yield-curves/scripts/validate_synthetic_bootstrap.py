"""Run and persist canonical validation on the synthetic F-TIIE bootstrap.

The canonical bootstrap is calibrated from the frozen synthetic OIS
quote set and then passed through the independent validation framework.

Persistent outputs
------------------
Tables:
    reports/tables/03_curve_validation/
        curve_validation_summary.csv
        independent_repricing.csv
        validation_issues.csv

Text:
    reports/text/03_curve_validation/
        curve_validation_report.txt

The validation-issues CSV is generated even when no issues are present,
leaving a header-only artifact for reproducibility.
"""

from pathlib import Path

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)
from yield_curves.validation import (
    validate_bootstrap_result,
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
    "03_curve_validation"
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

    validation_report = (
        validate_bootstrap_result(
            bootstrap_result=bootstrap_result,
            quotes=quotes,
            calendar=calendar,
        )
    )

    reference_date = (
        bootstrap_result
        .curve
        .reference_date
    )

    interpolation_method = (
        bootstrap_result
        .interpolation_method
        .value
    )

    curve_status = str(
        validation_report.status
    )

    # --------------------------------------------------------------
    # Persist validation summary.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="curve_validation_summary",
        header=(
            "reference_date",
            "interpolation_method",
            "curve_status",
            "calibration_quote_count",
            "curve_node_count",
            "converged_step_count",
            "passed_instrument_count",
            "review_instrument_count",
            "failed_instrument_count",
            "max_abs_repricing_error_bp",
            "mean_abs_repricing_error_bp",
            "warning_count",
            "critical_issue_count",
        ),
        rows=(
            (
                reference_date.isoformat(),
                interpolation_method,
                curve_status,
                validation_report.quote_count,
                validation_report.node_count,
                validation_report.converged_step_count,
                validation_report.passed_instrument_count,
                validation_report.review_instrument_count,
                validation_report.failed_instrument_count,
                validation_report.max_abs_repricing_error_bp,
                validation_report.mean_abs_repricing_error_bp,
                validation_report.warning_count,
                validation_report.critical_issue_count,
            ),
        ),
    )

    # --------------------------------------------------------------
    # Persist independent repricing checks.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="independent_repricing",
        header=(
            "reference_date",
            "interpolation_method",
            "tenor",
            "market_quote",
            "model_quote",
            "error_bp",
            "abs_error_bp",
            "status",
        ),
        rows=(
            (
                reference_date.isoformat(),
                interpolation_method,
                check.tenor,
                check.market_quote,
                check.model_quote,
                check.error_bp,
                abs(
                    check.error_bp
                ),
                str(
                    check.status
                ),
            )
            for check
            in validation_report.instrument_checks
        ),
    )

    # --------------------------------------------------------------
    # Persist validation issues.
    #
    # The CSV is deliberately created even when there are no issues.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="validation_issues",
        header=(
            "reference_date",
            "interpolation_method",
            "severity",
            "code",
            "message",
        ),
        rows=(
            (
                reference_date.isoformat(),
                interpolation_method,
                str(
                    issue.severity
                ),
                issue.code,
                issue.message,
            )
            for issue
            in validation_report.issues
        ),
    )

    # --------------------------------------------------------------
    # Build human-readable validation report.
    # --------------------------------------------------------------

    report = TextReport()

    report.line(
        "F-TIIE Curve Validation Report"
    )

    report.rule(
        character="=",
        width=72,
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
        f"Curve status         : "
        f"{curve_status}"
    )

    report.line(
        f"Calibration quotes   : "
        f"{validation_report.quote_count}"
    )

    report.line(
        f"Curve nodes          : "
        f"{validation_report.node_count}"
    )

    report.line(
        f"Converged steps      : "
        f"{validation_report.converged_step_count}"
    )

    report.line(
        f"PASS instruments     : "
        f"{validation_report.passed_instrument_count}"
    )

    report.line(
        f"REVIEW instruments   : "
        f"{validation_report.review_instrument_count}"
    )

    report.line(
        f"FAIL instruments     : "
        f"{validation_report.failed_instrument_count}"
    )

    report.line(
        f"Max repricing error  : "
        f"{validation_report.max_abs_repricing_error_bp:.8f} bp"
    )

    report.line(
        f"Mean repricing error : "
        f"{validation_report.mean_abs_repricing_error_bp:.8f} bp"
    )

    report.line(
        f"Warnings             : "
        f"{validation_report.warning_count}"
    )

    report.line(
        f"Critical issues      : "
        f"{validation_report.critical_issue_count}"
    )

    report.line()

    # --------------------------------------------------------------
    # Independent repricing table.
    # --------------------------------------------------------------

    report.line(
        "Independent Repricing"
    )

    report.rule(
        character="-",
        width=72,
    )

    report.line(
        f"{'Tenor':>5} "
        f"{'Market':>11} "
        f"{'Model':>11} "
        f"{'Error(bp)':>12} "
        f"{'Status':>12}"
    )

    report.rule(
        character="-",
        width=72,
    )

    for check in (
        validation_report.instrument_checks
    ):
        report.line(
            f"{check.tenor:>5} "
            f"{check.market_quote:>10.6%} "
            f"{check.model_quote:>10.6%} "
            f"{check.error_bp:>12.8f} "
            f"{str(check.status):>12}"
        )

    # --------------------------------------------------------------
    # Validation issues.
    # --------------------------------------------------------------

    if validation_report.issues:
        report.line()

        report.line(
            "Validation Issues"
        )

        report.rule(
            character="-",
            width=72,
        )

        for issue in (
            validation_report.issues
        ):
            report.line(
                f"[{issue.severity}] "
                f"{issue.code}: "
                f"{issue.message}"
            )

    else:
        report.line()

        report.line(
            "Validation Issues"
        )

        report.rule(
            character="-",
            width=72,
        )

        report.line(
            "None."
        )

    report.line()

    report.save(
        section=REPORT_SECTION,
        stem="curve_validation_report",
        echo=True,
    )


if __name__ == "__main__":
    main()