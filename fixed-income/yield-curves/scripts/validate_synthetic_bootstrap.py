"""Run canonical validation on the synthetic F-TIIE bootstrap."""

from pathlib import Path

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
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

    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
    )

    print(
        "F-TIIE Curve Validation Report"
    )

    print(
        "=" * 60
    )

    print()

    print(
        f"Curve status       : "
        f"{report.status}"
    )

    print(
        f"Calibration quotes : "
        f"{report.quote_count}"
    )

    print(
        f"Curve nodes        : "
        f"{report.node_count}"
    )

    print(
        f"Converged steps    : "
        f"{report.converged_step_count}"
    )

    print(
        f"PASS instruments   : "
        f"{report.passed_instrument_count}"
    )

    print(
        f"REVIEW instruments : "
        f"{report.review_instrument_count}"
    )

    print(
        f"FAIL instruments   : "
        f"{report.failed_instrument_count}"
    )

    print(
        f"Max repricing err  : "
        f"{report.max_abs_repricing_error_bp:.8f} bp"
    )

    print(
        f"Mean repricing err : "
        f"{report.mean_abs_repricing_error_bp:.8f} bp"
    )

    print(
        f"Warnings           : "
        f"{report.warning_count}"
    )

    print(
        f"Critical issues    : "
        f"{report.critical_issue_count}"
    )

    print()
    print(
        "Independent Repricing"
    )

    print(
        "-" * 60
    )

    print(
        f"{'Tenor':>5} "
        f"{'Market':>11} "
        f"{'Model':>11} "
        f"{'Error(bp)':>12} "
        f"{'Status':>10}"
    )

    for check in report.instrument_checks:
        print(
            f"{check.tenor:>5} "
            f"{check.market_quote:>10.6%} "
            f"{check.model_quote:>10.6%} "
            f"{check.error_bp:>12.8f} "
            f"{check.status:>10}"
        )

    if report.issues:
        print()
        print(
            "Validation Issues"
        )

        print(
            "-" * 60
        )

        for issue in report.issues:
            print(
                f"[{issue.severity}] "
                f"{issue.code}: "
                f"{issue.message}"
            )


if __name__ == "__main__":
    main()