"""Visual diagnostics for synthetic F-TIIE curve recovery.

The bootstrap receives only the frozen synthetic OIS quotes.

The known-truth curve is loaded only after calibration and is used
exclusively for recovery validation.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt

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


PROJECT_ROOT = Path(__file__).resolve().parents[1]

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


def year_fraction_act_360(
    start_date: date,
    end_date: date,
) -> float:
    """Return ACT/360 time between two dates."""

    return (
        end_date - start_date
    ).days / 360.0


def build_date_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int = 7,
) -> list[date]:
    """Build dense deterministic date grid."""

    if end_date < start_date:
        raise ValueError(
            "End date cannot precede start date."
        )

    dates: list[date] = []

    current = start_date

    while current < end_date:
        dates.append(current)
        current += timedelta(days=step_days)

    if not dates or dates[-1] != end_date:
        dates.append(end_date)

    return dates


def build_recovery_objects():
    """Calibrate recovered curve and build hidden true curve."""

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

    recovered_curve = result.curve

    # IMPORTANT:
    # The known-truth curve is introduced only after bootstrap.
    true_curve = build_synthetic_known_truth_curve(
        recovered_curve.reference_date
    )

    return (
        quotes,
        result,
        true_curve,
        recovered_curve,
    )


def plot_discount_factor_recovery(
    *,
    result,
    true_curve,
    recovered_curve,
) -> None:
    """Plot true and recovered discount-factor curves."""

    reference_date = (
        recovered_curve.reference_date
    )

    last_date = (
        recovered_curve.last_node_date
    )

    dates = build_date_grid(
        start_date=reference_date,
        end_date=last_date,
        step_days=7,
    )

    times = [
        year_fraction_act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    true_dfs = [
        true_curve.discount_factor(
            target_date
        )
        for target_date in dates
    ]

    recovered_dfs = [
        recovered_curve.discount_factor(
            target_date
        )
        for target_date in dates
    ]

    pillar_dates = [
        step.pillar_date
        for step in result.steps
    ]

    pillar_times = [
        year_fraction_act_360(
            reference_date,
            pillar_date,
        )
        for pillar_date in pillar_dates
    ]

    solved_dfs = [
        step.solved_discount_factor
        for step in result.steps
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_dfs,
        linewidth=2,
        label="True synthetic curve",
    )

    ax.plot(
        times,
        recovered_dfs,
        linewidth=2,
        linestyle="--",
        label="Recovered curve",
    )

    ax.scatter(
        pillar_times,
        solved_dfs,
        marker="o",
        label="Calibrated pillars",
        zorder=3,
    )

    ax.set_title(
        "Discount-Factor Recovery"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Discount factor"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def plot_discount_factor_errors(
    *,
    result,
    true_curve,
) -> None:
    """Plot recovered-minus-true DF error at calibration pillars."""

    reference_date = (
        result.curve.reference_date
    )

    pillar_times = []
    errors = []
    tenors = []

    for step in result.steps:
        true_df = (
            true_curve.discount_factor(
                step.pillar_date
            )
        )

        error = (
            step.solved_discount_factor
            - true_df
        )

        pillar_times.append(
            year_fraction_act_360(
                reference_date,
                step.pillar_date,
            )
        )

        errors.append(
            error
        )

        tenors.append(
            step.tenor
        )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.axhline(
        0.0,
        linewidth=1,
    )

    ax.plot(
        pillar_times,
        errors,
        marker="o",
        linewidth=1.5,
    )

    for x, y, tenor in zip(
        pillar_times,
        errors,
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
        "Discount-Factor Recovery Error by Pillar"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Recovered DF - True DF"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    fig.tight_layout()

    plt.show()


def plot_zero_rate_recovery(
    *,
    true_curve,
    recovered_curve,
) -> None:
    """Plot true and recovered continuously compounded zero curves."""

    reference_date = (
        recovered_curve.reference_date
    )

    # Start one day after reference because the true zero rate at
    # t=0 is conceptually defined by the parametric curve, while the
    # nodal curve's t=0 reporting value is inferred from its first node.
    start_date = (
        reference_date
        + timedelta(days=1)
    )

    last_date = (
        recovered_curve.last_node_date
    )

    dates = build_date_grid(
        start_date=start_date,
        end_date=last_date,
        step_days=7,
    )

    times = [
        year_fraction_act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    true_zero_rates = [
        true_curve.zero_rate(
            target_date
        )
        * 100
        for target_date in dates
    ]

    recovered_zero_rates = [
        recovered_curve.zero_rate(
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
        true_zero_rates,
        linewidth=2,
        label="True synthetic zero curve",
    )

    ax.plot(
        times,
        recovered_zero_rates,
        linewidth=2,
        linestyle="--",
        label="Recovered zero curve",
    )

    ax.set_title(
        "Zero-Rate Recovery"
    )

    ax.set_xlabel(
        "Years from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "Continuously compounded zero rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def plot_forward_rate_recovery(
    *,
    true_curve,
    recovered_curve,
) -> None:
    """Plot true and recovered 28-day simple forward curves."""

    reference_date = (
        recovered_curve.reference_date
    )

    forward_days = 28

    last_start_date = (
        recovered_curve.last_node_date
        - timedelta(days=forward_days)
    )

    start_dates = build_date_grid(
        start_date=reference_date,
        end_date=last_start_date,
        step_days=7,
    )

    times = [
        year_fraction_act_360(
            reference_date,
            start_date,
        )
        for start_date in start_dates
    ]

    true_forwards = []
    recovered_forwards = []

    for start_date in start_dates:
        end_date = (
            start_date
            + timedelta(days=forward_days)
        )

        true_forwards.append(
            true_curve.forward_rate(
                start_date,
                end_date,
            )
            * 100
        )

        recovered_forwards.append(
            recovered_curve.forward_rate(
                start_date,
                end_date,
            )
            * 100
        )

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_forwards,
        linewidth=2,
        label="True synthetic 28D forward",
    )

    ax.plot(
        times,
        recovered_forwards,
        linewidth=2,
        linestyle="--",
        label="Recovered 28D forward",
    )

    ax.set_title(
        "28-Day Forward-Rate Recovery"
    )

    ax.set_xlabel(
        "Forward start time from reference date (ACT/360)"
    )

    ax.set_ylabel(
        "28-day simple forward rate (%)"
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    plt.show()


def main() -> None:
    (
        _,
        result,
        true_curve,
        recovered_curve,
    ) = build_recovery_objects()

    plot_discount_factor_recovery(
        result=result,
        true_curve=true_curve,
        recovered_curve=recovered_curve,
    )

    plot_discount_factor_errors(
        result=result,
        true_curve=true_curve,
    )

    plot_zero_rate_recovery(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
    )

    plot_forward_rate_recovery(
        true_curve=true_curve,
        recovered_curve=recovered_curve,
    )


if __name__ == "__main__":
    main()