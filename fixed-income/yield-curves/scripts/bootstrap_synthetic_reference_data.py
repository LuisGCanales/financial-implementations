"""Bootstrap the frozen synthetic F-TIIE OIS quote dataset."""

from pathlib import Path

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
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

    print(
        "Synthetic F-TIIE OIS Bootstrap"
    )

    print(
        f"Reference date: "
        f"{result.curve.reference_date}"
    )

    print()

    print(
        f"{'Tenor':>5} "
        f"{'Quote':>10} "
        f"{'Model':>10} "
        f"{'Err(bp)':>10} "
        f"{'Solved DF':>12} "
        f"{'True DF':>12} "
        f"{'DF Diff':>12}"
    )

    print(
        "-" * 90
    )

    for step in result.steps:
        true_df = (
            true_curve.discount_factor(
                step.pillar_date
            )
        )

        df_difference = (
            step.solved_discount_factor
            - true_df
        )

        print(
            f"{step.tenor:>5} "
            f"{step.market_quote:>9.5%} "
            f"{step.model_quote:>9.5%} "
            f"{step.quote_error_bp:>10.6f} "
            f"{step.solved_discount_factor:>12.8f} "
            f"{true_df:>12.8f} "
            f"{df_difference:>12.8f}"
        )

    print()
    print(
        "All calibration instruments should "
        "reprice to approximately zero error."
    )

    print(
        "Recovered DFs need not exactly match "
        "the true parametric curve because the "
        "bootstrap uses a different interpolation family."
    )


if __name__ == "__main__":
    main()