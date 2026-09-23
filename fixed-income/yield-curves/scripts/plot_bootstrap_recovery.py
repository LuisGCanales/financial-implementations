"""Visual diagnostics for synthetic F-TIIE curve recovery.

The bootstrap receives only the frozen synthetic OIS quotes.

The known-truth curve is loaded only after calibration and is used
exclusively for recovery validation.

Persistent outputs
------------------
Figures:
    reports/figures/02_bootstrap_recovery/
        discount_factor_recovery.png
        discount_factor_recovery.svg
        discount_factor_error_by_pillar.png
        discount_factor_error_by_pillar.svg
        zero_rate_recovery.png
        zero_rate_recovery.svg
        forward_28d_recovery.png
        forward_28d_recovery.svg

Tables:
    reports/tables/02_bootstrap_recovery/
        discount_factor_recovery_dense.csv
        discount_factor_error_by_pillar.csv
        zero_rate_recovery_dense.csv
        forward_28d_recovery_dense.csv
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
from yield_curves.reporting import (
    save_csv,
    save_figure,
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

REPORT_SECTION = (
    "02_bootstrap_recovery"
)

DENSE_GRID_STEP_DAYS = 7
FORWARD_PERIOD_DAYS = 28


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
    step_days: int = DENSE_GRID_STEP_DAYS,
) -> list[date]:
    """Build dense deterministic date grid."""

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
    """Plot and persist true vs recovered discount-factor curves."""

    reference_date = (
        recovered_curve.reference_date
    )

    last_date = (
        recovered_curve.last_node_date
    )

    dates = build_date_grid(
        start_date=reference_date,
        end_date=last_date,
        step_days=DENSE_GRID_STEP_DAYS,
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

    # --------------------------------------------------------------
    # Persist dense numerical series.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="discount_factor_recovery_dense",
        header=(
            "date",
            "act360_years",
            "true_discount_factor",
            "recovered_discount_factor",
            "df_error",
        ),
        rows=(
            (
                target_date.isoformat(),
                times[index],
                true_dfs[index],
                recovered_dfs[index],
                (
                    recovered_dfs[index]
                    - true_dfs[index]
                ),
            )
            for index, target_date
            in enumerate(
                dates
            )
        ),
    )

    # --------------------------------------------------------------
    # Plot.
    # --------------------------------------------------------------

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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="discount_factor_recovery",
    )

    plt.show()


def plot_discount_factor_errors(
    *,
    result,
    true_curve,
) -> None:
    """Plot and persist recovered-minus-true DF error by pillar."""

    reference_date = (
        result.curve.reference_date
    )

    pillar_times: list[float] = []
    errors: list[float] = []
    tenors: list[str] = []
    pillar_dates: list[date] = []
    solved_dfs: list[float] = []
    true_dfs: list[float] = []

    for step in result.steps:
        true_df = (
            true_curve.discount_factor(
                step.pillar_date
            )
        )

        solved_df = (
            step.solved_discount_factor
        )

        error = (
            solved_df
            - true_df
        )

        pillar_dates.append(
            step.pillar_date
        )

        pillar_times.append(
            year_fraction_act_360(
                reference_date,
                step.pillar_date,
            )
        )

        solved_dfs.append(
            solved_df
        )

        true_dfs.append(
            true_df
        )

        errors.append(
            error
        )

        tenors.append(
            step.tenor
        )

    # --------------------------------------------------------------
    # Persist pillar-level recovery table.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="discount_factor_error_by_pillar",
        header=(
            "tenor",
            "pillar_date",
            "act360_years",
            "solved_discount_factor",
            "true_discount_factor",
            "df_error",
            "relative_error_ppm",
        ),
        rows=(
            (
                tenors[index],
                pillar_dates[index].isoformat(),
                pillar_times[index],
                solved_dfs[index],
                true_dfs[index],
                errors[index],
                (
                    solved_dfs[index]
                    / true_dfs[index]
                    - 1.0
                )
                * 1_000_000.0,
            )
            for index in range(
                len(
                    tenors
                )
            )
        ),
    )

    # --------------------------------------------------------------
    # Plot.
    # --------------------------------------------------------------

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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="discount_factor_error_by_pillar",
    )

    plt.show()


def plot_zero_rate_recovery(
    *,
    true_curve,
    recovered_curve,
) -> None:
    """Plot and persist true vs recovered continuous zero curves."""

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
        step_days=DENSE_GRID_STEP_DAYS,
    )

    times = [
        year_fraction_act_360(
            reference_date,
            target_date,
        )
        for target_date in dates
    ]

    # Raw decimal rates are persisted.
    true_zero_rates = [
        true_curve.zero_rate(
            target_date
        )
        for target_date in dates
    ]

    recovered_zero_rates = [
        recovered_curve.zero_rate(
            target_date
        )
        for target_date in dates
    ]

    # --------------------------------------------------------------
    # Persist dense zero-rate series.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="zero_rate_recovery_dense",
        header=(
            "date",
            "act360_years",
            "true_zero_rate",
            "recovered_zero_rate",
            "error_bp",
        ),
        rows=(
            (
                target_date.isoformat(),
                times[index],
                true_zero_rates[index],
                recovered_zero_rates[index],
                (
                    recovered_zero_rates[index]
                    - true_zero_rates[index]
                )
                * 10_000.0,
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

    true_zero_rates_pct = [
        rate * 100.0
        for rate in true_zero_rates
    ]

    recovered_zero_rates_pct = [
        rate * 100.0
        for rate in recovered_zero_rates
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_zero_rates_pct,
        linewidth=2,
        label="True synthetic zero curve",
    )

    ax.plot(
        times,
        recovered_zero_rates_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="zero_rate_recovery",
    )

    plt.show()


def plot_forward_rate_recovery(
    *,
    true_curve,
    recovered_curve,
) -> None:
    """Plot and persist true vs recovered 28-day simple forwards."""

    reference_date = (
        recovered_curve.reference_date
    )

    forward_days = (
        FORWARD_PERIOD_DAYS
    )

    last_start_date = (
        recovered_curve.last_node_date
        - timedelta(
            days=forward_days
        )
    )

    start_dates = build_date_grid(
        start_date=reference_date,
        end_date=last_start_date,
        step_days=DENSE_GRID_STEP_DAYS,
    )

    times = [
        year_fraction_act_360(
            reference_date,
            start_date,
        )
        for start_date in start_dates
    ]

    end_dates: list[date] = []
    true_forwards: list[float] = []
    recovered_forwards: list[float] = []

    for start_date in start_dates:
        end_date = (
            start_date
            + timedelta(
                days=forward_days
            )
        )

        end_dates.append(
            end_date
        )

        true_forwards.append(
            true_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        recovered_forwards.append(
            recovered_curve.forward_rate(
                start_date,
                end_date,
            )
        )

    # --------------------------------------------------------------
    # Persist raw decimal-rate forward series.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="forward_28d_recovery_dense",
        header=(
            "start_date",
            "end_date",
            "start_act360_years",
            "true_forward_rate",
            "recovered_forward_rate",
            "error_bp",
        ),
        rows=(
            (
                start_dates[index].isoformat(),
                end_dates[index].isoformat(),
                times[index],
                true_forwards[index],
                recovered_forwards[index],
                (
                    recovered_forwards[index]
                    - true_forwards[index]
                )
                * 10_000.0,
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

    true_forwards_pct = [
        rate * 100.0
        for rate in true_forwards
    ]

    recovered_forwards_pct = [
        rate * 100.0
        for rate in recovered_forwards
    ]

    fig, ax = plt.subplots(
        figsize=(10, 5.5)
    )

    ax.plot(
        times,
        true_forwards_pct,
        linewidth=2,
        label="True synthetic 28D forward",
    )

    ax.plot(
        times,
        recovered_forwards_pct,
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

    save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem="forward_28d_recovery",
    )

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