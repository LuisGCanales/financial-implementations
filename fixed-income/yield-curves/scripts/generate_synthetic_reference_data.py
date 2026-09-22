"""Generate canonical synthetic F-TIIE OIS reference quotes."""

from datetime import date
from pathlib import Path

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.schedules import (
    calculate_effective_date,
)
from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
    generate_synthetic_ois_quotes,
    write_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


TRADE_DATE = date(
    2026,
    9,
    15,
)


def main() -> None:
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

    output_path = (
        PROJECT_ROOT
        / "data"
        / "synthetic"
        / "ftiie_ois_quotes_v1.csv"
    )

    write_synthetic_ois_quotes_csv(
        quotes=quotes,
        path=output_path,
    )

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