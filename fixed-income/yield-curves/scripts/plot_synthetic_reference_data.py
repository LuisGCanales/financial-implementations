"""Plot and persist synthetic known-truth reference data.

This script produces the visual reference layer for the controlled
synthetic F-TIIE experiment.

Persistent outputs
------------------
Figures:
    reports/figures/01_synthetic_reference/
        known_truth_zero_curve.png
        known_truth_zero_curve.svg
        known_truth_forward_28d.png
        known_truth_forward_28d.svg
        synthetic_ois_par_curve.png
        synthetic_ois_par_curve.svg

Tables:
    reports/tables/01_synthetic_reference/
        known_truth_zero_curve_dense.csv
        known_truth_forward_28d_dense.csv
        synthetic_ois_par_quotes.csv

Rates are persisted in raw decimal form.
Percentage conversion is used only for plotting.
"""

from __future__ import annotations

import csv

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.reporting import (
    save_csv,
    save_figure,
)
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

REPORT_SECTION = (
    "01_synthetic_reference"
)

REFERENCE_DATE = date(
    2026,
    9,
    18,
)

DENSE_GRID_STEP_DAYS = 7
FORWARD_PERIOD_DAYS = 28
REFERENCE_HORIZON_YEARS = 30


def year_fraction_act_360(
    start: date,
    end: date,
) -> float:
    """Return ACT/360 year fraction for plotting."""

    return (
        end - start
    ).days / 360.0


def build_dense_curve_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int = DENSE_GRID_STEP_DAYS,
) -> list[date]:
    """Generate dense deterministic date grid for visualization."""

    if step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    if end_date < start_date:
        raise ValueError(
            "End date cannot precede start date."
        )

    dates: list[date] = []

    current = start_date

    while current < end_date:
        dates.append(
            current
        )

        current += timedelta(
            days=step_days
        )

    if not dates or dates[-1] != end_date:
        dates.append(
            end_date
        )

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
            csv.DictReader(
                file
            )
        )


def plot_known_truth_zero_curve() -> None:
    """Plot and persist synthetic continuous zero curve."""

    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    end_date = date(
        REFERENCE_DATE.year
        + REFERENCE_HORIZON_YEARS,
        REFERENCE_DATE.month,
        REFERENCE_DATE.day,
    )

    dates = build_dense_curve_grid(
        start_date=REFERENCE_DATE,
        end_date=end_date,
        step_days=DENSE_GRID_STEP_DAYS,
    )

    times = [
        year_fraction_act_360(
            REFERENCE_DATE,
            target_date,
        )
        for target_date in dates
    ]

    # --------------------------------------------------------------
    # Raw decimal rates are persisted.
    # --------------------------------------------------------------

    zero_rates = [
        curve.zero_rate(
            target_date
        )
        for target_date in dates
    ]

    save_csv(
        section=REPORT_SECTION,
        stem="known_truth_zero_curve_dense",
        header=(
            "date",
            "act360_years",
            "zero_rate",
        ),
        rows=(
            (
                target_date.isoformat(),
                times[index],
                zero_rates[index],
            )
            for index, target_date
            in enumerate(
                dates
            )
        ),
    )

    # --------------------------------------------------------------
    # Convert to percentage points only for presentation.
    # --------------------------------------------------------------

    zero_rates_pct = [
        rate * 100.0
        for rate in zero_rates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        zero_rates_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="known_truth_zero_curve",
    )

    plt.show()


def plot_synthetic_par_curve() -> None:
    """Plot and persist synthetic F-TIIE OIS par quotes."""

    rows = load_synthetic_quotes(
        QUOTES_PATH
    )

    maturities = [
        date.fromisoformat(
            row[
                "contractual_maturity_date"
            ]
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

    # --------------------------------------------------------------
    # Raw decimal par rates are persisted.
    # --------------------------------------------------------------

    par_rates = [
        float(
            row[
                "par_rate"
            ]
        )
        for row in rows
    ]

    tenors = [
        row[
            "tenor"
        ]
        for row in rows
    ]

    save_csv(
        section=REPORT_SECTION,
        stem="synthetic_ois_par_quotes",
        header=(
            "tenor",
            "contractual_maturity_date",
            "act360_years",
            "par_rate",
        ),
        rows=(
            (
                tenors[index],
                maturities[
                    index
                ].isoformat(),
                times[index],
                par_rates[index],
            )
            for index in range(
                len(
                    rows
                )
            )
        ),
    )

    # --------------------------------------------------------------
    # Convert to percentage points only for presentation.
    # --------------------------------------------------------------

    par_rates_pct = [
        rate * 100.0
        for rate in par_rates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        par_rates_pct,
        marker="o",
        linewidth=2,
    )

    for x, y, tenor in zip(
        times,
        par_rates_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="synthetic_ois_par_curve",
    )

    plt.show()


def plot_synthetic_forward_curve() -> None:
    """Plot and persist synthetic 28-day simple forward rates."""

    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    final_date = date(
        REFERENCE_DATE.year
        + REFERENCE_HORIZON_YEARS,
        REFERENCE_DATE.month,
        REFERENCE_DATE.day,
    )

    # The forward needs an end date 28 days after its start,
    # so the start grid must stop before the final horizon.
    last_forward_start = (
        final_date
        - timedelta(
            days=FORWARD_PERIOD_DAYS
        )
    )

    start_dates = build_dense_curve_grid(
        start_date=REFERENCE_DATE,
        end_date=last_forward_start,
        step_days=DENSE_GRID_STEP_DAYS,
    )

    times = [
        year_fraction_act_360(
            REFERENCE_DATE,
            start_date,
        )
        for start_date in start_dates
    ]

    end_dates: list[date] = []
    forward_rates: list[float] = []

    for start_date in start_dates:
        end_date = (
            start_date
            + timedelta(
                days=FORWARD_PERIOD_DAYS
            )
        )

        forward_rate = (
            curve.forward_rate(
                start_date,
                end_date,
            )
        )

        end_dates.append(
            end_date
        )

        forward_rates.append(
            forward_rate
        )

    # --------------------------------------------------------------
    # Persist raw decimal forward rates.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="known_truth_forward_28d_dense",
        header=(
            "start_date",
            "end_date",
            "start_act360_years",
            "forward_period_days",
            "forward_rate",
        ),
        rows=(
            (
                start_dates[
                    index
                ].isoformat(),
                end_dates[
                    index
                ].isoformat(),
                times[index],
                FORWARD_PERIOD_DAYS,
                forward_rates[index],
            )
            for index in range(
                len(
                    start_dates
                )
            )
        ),
    )

    # --------------------------------------------------------------
    # Convert to percentage points only for presentation.
    # --------------------------------------------------------------

    forward_rates_pct = [
        rate * 100.0
        for rate in forward_rates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        forward_rates_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="known_truth_forward_28d",
    )

    plt.show()


def main() -> None:
    plot_known_truth_zero_curve()

    plot_synthetic_forward_curve()

    plot_synthetic_par_curve()


if __name__ == "__main__":
    main()