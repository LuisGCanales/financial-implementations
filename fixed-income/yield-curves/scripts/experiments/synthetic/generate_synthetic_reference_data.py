"""Generate candidate synthetic F-TIIE OIS reference quotes for human review."""

import argparse
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from yield_curves.tooling.reference_candidates import validate_candidate_path, write_candidate

from yield_curves.tooling.project_paths import (find_project_root)

from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.schedules import (
    calculate_effective_date,
)
from yield_curves.research.synthetic import (build_synthetic_known_truth_curve, generate_synthetic_ois_quotes, write_synthetic_ois_quotes_csv)


PROJECT_ROOT = (
    find_project_root(Path(__file__))
)


TRADE_DATE = date(
    2026,
    9,
    15,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New candidate CSV path; frozen and existing paths are rejected.")
    args = parser.parse_args()
    try:
        validate_candidate_path(args.output, root=PROJECT_ROOT)
    except ValueError as error:
        parser.error(str(error))

    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    effective_date = calculate_effective_date(
        TRADE_DATE,
        calendar,
    )

    true_curve = (
        build_synthetic_known_truth_curve(
            effective_date
        )
    )

    quotes = generate_synthetic_ois_quotes(
        trade_date=TRADE_DATE,
        calendar=calendar,
        true_curve=true_curve,
    )

    output_path = args.output
    # Reuse the deterministic CSV serializer without allowing its overwrite
    # behavior at the user destination.
    with TemporaryDirectory(prefix="ftiie-candidate-") as temporary:
        staged = Path(temporary) / "quotes.csv"
        write_synthetic_ois_quotes_csv(quotes=quotes, path=staged)
        write_candidate(output_path, staged.read_bytes(), root=PROJECT_ROOT)

    print(
        f"Synthetic scenario: "
        f"{quotes[0].scenario_id}"
    )

    print(
        f"Trade date: {TRADE_DATE}"
    )

    print(
        f"Effective date: {effective_date}"
    )

    print()

    print(
        f"{'Tenor':>5} "
        f"{'Par Rate':>12} "
        f"{'Periods':>9} "
        f"{'Final Payment':>14}"
    )

    print(
        "-" * 45
    )

    for quote in quotes:
        print(
            f"{quote.tenor:>5} "
            f"{quote.par_rate:>11.6%} "
            f"{quote.number_of_periods:>9} "
            f"{quote.final_payment_date}"
        )

    print()
    print(
        f"Wrote: {output_path}"
    )


if __name__ == "__main__":
    main()