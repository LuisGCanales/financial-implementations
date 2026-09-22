"""Plot the synthetic known-truth zero curve and synthetic OIS par quotes."""

from __future__ import annotations

import csv

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)

REFERENCE_DATE = date(
    2026,
    9,
    18,
)


def year_fraction_act_360(
    start: date,
    end: date,
) -> float:
    """Return ACT/360 year fraction for plotting."""

    return (end - start).days / 360.0


def build_dense_curve_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int = 7,
) -> list[date]:
    """Generate dense date grid for visualization."""

    dates = []

    current = start_date

    while current < end_date:
        dates.append(current)
        current += timedelta(days=step_days)

    dates.append(end_date)

    return dates


def load_synthetic_quotes(
    path: Path,
) -> list[dict[str, str]]:
    """Load frozen synthetic OIS quote dataset."""

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def plot_known_truth_zero_curve() -> None:
    """Plot synthetic continuously compounded zero curve."""

    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    end_date = date(
        REFERENCE_DATE.year + 30,
        REFERENCE_DATE.month,
        REFERENCE_DATE.day,
    )

    dates = build_dense_curve_grid(
        start_date=REFERENCE_DATE,
        end_date=end_date,
        step_days=7,
    )

    times = [
        year_fraction_act_360(
            REFERENCE_DATE,
            target_date,
        )
        for target_date in dates
    ]

    zero_rates = [
        curve.zero_rate(
            target_date
        )
        * 100
        for target_date in dates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        zero_rates,
        linewidth=2,
    )

    ax.set_title(
        "Synthetic Known-Truth Zero Curve"
    )

    ax.set_xlabel(
        "Years from curve reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Continuously compounded zero rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    plt.show()


def plot_synthetic_par_curve() -> None:
    """Plot synthetic F-TIIE OIS par quotes."""

    rows = load_synthetic_quotes(
        QUOTES_PATH
    )

    maturities = [
        date.fromisoformat(
            row["contractual_maturity_date"]
        )
        for row in rows
    ]

    times = [
        year_fraction_act_360(
            REFERENCE_DATE,
            maturity,
        )
        for maturity in maturities
    ]

    par_rates = [
        float(
            row["par_rate"]
        )
        * 100
        for row in rows
    ]

    tenors = [
        row["tenor"]
        for row in rows
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        par_rates,
        marker="o",
        linewidth=2,
    )

    for x, y, tenor in zip(
        times,
        par_rates,
        tenors,
    ):
        ax.annotate(
            tenor,
            xy=(x, y),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )

    ax.set_title(
        "Synthetic F-TIIE OIS Par Curve"
    )

    ax.set_xlabel(
        "Years from curve reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Par OIS rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    plt.show()


def plot_synthetic_forward_curve() -> None:
    """Plot synthetic 28-day simple forward rates."""

    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    forward_period_days = 28

    final_date = date(
        REFERENCE_DATE.year + 30,
        REFERENCE_DATE.month,
        REFERENCE_DATE.day,
    )

    # The forward needs an end date 28 days after its start,
    # so the start grid must stop before the final horizon.
    last_forward_start = (
        final_date
        - timedelta(days=forward_period_days)
    )

    start_dates = build_dense_curve_grid(
        start_date=REFERENCE_DATE,
        end_date=last_forward_start,
        step_days=7,
    )

    times = [
        year_fraction_act_360(
            REFERENCE_DATE,
            start_date,
        )
        for start_date in start_dates
    ]

    forward_rates = []

    for start_date in start_dates:
        end_date = (
            start_date
            + timedelta(days=forward_period_days)
        )

        forward_rate = curve.forward_rate(
            start_date,
            end_date,
        )

        forward_rates.append(
            forward_rate * 100
        )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        forward_rates,
        linewidth=2,
    )

    ax.set_title(
        "Synthetic 28-Day Forward Curve"
    )

    ax.set_xlabel(
        "Forward start time from curve reference date (ACT/360)"
    )

    ax.set_ylabel(
        "28-day simple forward rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    plt.show()
    

def main() -> None:
    plot_known_truth_zero_curve()
    plot_synthetic_forward_curve()
    plot_synthetic_par_curve()


if __name__ == "__main__":
    main()