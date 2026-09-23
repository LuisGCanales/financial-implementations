"""Bootstrap and report the frozen synthetic F-TIIE OIS quote dataset.

The calibration uses only the frozen synthetic OIS quotes.

The known-truth curve is introduced only after calibration and is used
exclusively for recovery validation.

Persistent outputs
------------------
Tables:
    reports/tables/02_bootstrap_recovery/
        bootstrap_node_recovery.csv

Text:
    reports/text/02_bootstrap_recovery/
        bootstrap_node_recovery.txt

Rates are persisted in raw decimal form.
Basis-point and ppm transformations are used only for diagnostics.
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

REPORT_SECTION = (
    "02_bootstrap_recovery"
)


def main() -> None:
    quotes = read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    result = bootstrap_ftiie_ois_curve(
        quotes=quotes,
        calendar=calendar,
    )

    # IMPORTANT:
    # The true curve enters only AFTER calibration,
    # exclusively for recovery validation.
    true_curve = (
        build_synthetic_known_truth_curve(
            result.curve.reference_date
        )
    )

    reference_date = (
        result.curve.reference_date
    )

    interpolation_method = (
        result.interpolation_method.value
    )

    # --------------------------------------------------------------
    # Build reusable nodal recovery records.
    # --------------------------------------------------------------

    recovery_rows = []

    for step in result.steps:
        true_df = (
            true_curve.discount_factor(
                step.pillar_date
            )
        )

        solved_df = (
            step.solved_discount_factor
        )

        df_difference = (
            solved_df
            - true_df
        )

        relative_error_ppm = (
            solved_df
            / true_df
            - 1.0
        ) * 1_000_000.0

        recovery_rows.append(
            (
                reference_date.isoformat(),
                interpolation_method,
                step.tenor,
                step.pillar_date.isoformat(),
                step.market_quote,
                step.model_quote,
                step.quote_error_bp,
                solved_df,
                true_df,
                df_difference,
                relative_error_ppm,
            )
        )

    # --------------------------------------------------------------
    # Persist machine-readable output.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="bootstrap_node_recovery",
        header=(
            "reference_date",
            "interpolation_method",
            "tenor",
            "pillar_date",
            "market_quote",
            "model_quote",
            "quote_error_bp",
            "solved_discount_factor",
            "true_discount_factor",
            "df_difference",
            "relative_error_ppm",
        ),
        rows=recovery_rows,
    )

    # --------------------------------------------------------------
    # Build human-readable report.
    # --------------------------------------------------------------

    report = TextReport()

    report.line(
        "Synthetic F-TIIE OIS Bootstrap"
    )

    report.rule(
        character="=",
        width=90,
    )

    report.line()

    report.line(
        f"Reference date: "
        f"{reference_date}"
    )

    report.line(
        f"Interpolation method: "
        f"{interpolation_method}"
    )

    report.line(
        f"Calibration instruments: "
        f"{len(result.steps)}"
    )

    report.line()

    report.line(
        f"{'Tenor':>5} "
        f"{'Quote':>10} "
        f"{'Model':>10} "
        f"{'Err(bp)':>10} "
        f"{'Solved DF':>12} "
        f"{'True DF':>12} "
        f"{'DF Diff':>12} "
        f"{'Rel(ppm)':>12}"
    )

    report.rule(
        character="-",
        width=103,
    )

    for step in result.steps:
        true_df = (
            true_curve.discount_factor(
                step.pillar_date
            )
        )

        solved_df = (
            step.solved_discount_factor
        )

        df_difference = (
            solved_df
            - true_df
        )

        relative_error_ppm = (
            solved_df
            / true_df
            - 1.0
        ) * 1_000_000.0

        report.line(
            f"{step.tenor:>5} "
            f"{step.market_quote:>9.5%} "
            f"{step.model_quote:>9.5%} "
            f"{step.quote_error_bp:>10.6f} "
            f"{solved_df:>12.8f} "
            f"{true_df:>12.8f} "
            f"{df_difference:>12.8f} "
            f"{relative_error_ppm:>12.3f}"
        )

    report.line()

    report.line(
        "All calibration instruments should "
        "reprice to approximately zero error."
    )

    report.line(
        "Recovered discount factors need not exactly "
        "match the true parametric curve because the "
        "bootstrap uses a different interpolation family."
    )

    report.line(
        "The known-truth curve is used only after "
        "calibration for recovery analysis."
    )

    report.save(
        section=REPORT_SECTION,
        stem="bootstrap_node_recovery",
        echo=True,
    )


if __name__ == "__main__":
    main()