"""Report and persist curve-shape diagnostics for the canonical bootstrap.

The canonical synthetic F-TIIE curve is calibrated first and then
analyzed for forward-curve shape characteristics.

Persistent outputs
------------------
Tables:
    reports/tables/04_curve_diagnostics/
        curve_diagnostics_summary.csv
        log_linear_forward_jumps.csv

Text:
    reports/text/04_curve_diagnostics/
        curve_diagnostics.txt

The jump table is generated even when the selected interpolation method
does not expose log-linear segment diagnostics, leaving a header-only
artifact in that case.
"""

from pathlib import Path

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.diagnostics import (
    analyze_curve,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
)
from yield_curves.synthetic import (
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
    "04_curve_diagnostics"
)

FORWARD_PERIOD_DAYS = 28
GRID_STEP_DAYS = 7


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

    curve = (
        bootstrap_result.curve
    )

    reference_date = (
        curve.reference_date
    )

    interpolation_method = (
        bootstrap_result
        .interpolation_method
        .value
    )

    diagnostics = analyze_curve(
        curve=curve,
        last_supported_date=(
            curve.last_node_date
        ),
        forward_period_days=(
            FORWARD_PERIOD_DAYS
        ),
        grid_step_days=(
            GRID_STEP_DAYS
        ),
    )

    summary = (
        diagnostics.forward_summary
    )

    log_linear = (
        diagnostics.log_linear
    )

    # --------------------------------------------------------------
    # Persist diagnostic summary.
    # --------------------------------------------------------------

    save_csv(
        section=REPORT_SECTION,
        stem="curve_diagnostics_summary",
        header=(
            "reference_date",
            "interpolation_method",
            "forward_period_days",
            "grid_step_days",
            "observation_count",
            "minimum_forward_rate",
            "minimum_forward_rate_date",
            "maximum_forward_rate",
            "maximum_forward_rate_date",
            "mean_forward_rate",
            "forward_standard_deviation",
            "forward_standard_deviation_bp",
            "maximum_local_change_bp",
            "maximum_local_change_date",
            "log_linear_segment_count",
            "log_linear_jump_count",
            "mean_absolute_jump_bp",
            "maximum_absolute_jump_bp",
            "maximum_absolute_jump_date",
        ),
        rows=(
            (
                reference_date.isoformat(),
                interpolation_method,
                FORWARD_PERIOD_DAYS,
                GRID_STEP_DAYS,
                summary.observation_count,
                summary.minimum_rate,
                summary.minimum_rate_date.isoformat(),
                summary.maximum_rate,
                summary.maximum_rate_date.isoformat(),
                summary.mean_rate,
                summary.standard_deviation,
                (
                    summary.standard_deviation
                    * 10_000.0
                ),
                summary.maximum_local_change_bp,
                summary.maximum_local_change_date.isoformat(),
                (
                    ""
                    if log_linear is None
                    else len(
                        log_linear.segments
                    )
                ),
                (
                    ""
                    if log_linear is None
                    else len(
                        log_linear.jumps
                    )
                ),
                (
                    ""
                    if log_linear is None
                    else (
                        log_linear
                        .mean_absolute_jump_bp
                    )
                ),
                (
                    ""
                    if log_linear is None
                    else (
                        log_linear
                        .maximum_absolute_jump_bp
                    )
                ),
                (
                    ""
                    if log_linear is None
                    else (
                        log_linear
                        .maximum_absolute_jump_date
                        .isoformat()
                    )
                ),
            ),
        ),
    )

    # --------------------------------------------------------------
    # Persist exact log-linear forward jumps.
    #
    # The file is still produced with headers if log-linear-specific
    # diagnostics are unavailable.
    # --------------------------------------------------------------

    jump_rows = (
        ()
        if log_linear is None
        else tuple(
            (
                reference_date.isoformat(),
                interpolation_method,
                index,
                jump.pillar_date.isoformat(),
                jump.left_forward_rate,
                jump.right_forward_rate,
                jump.jump_bp,
                abs(
                    jump.jump_bp
                ),
            )
            for index, jump
            in enumerate(
                log_linear.jumps,
                start=1,
            )
        )
    )

    save_csv(
        section=REPORT_SECTION,
        stem="log_linear_forward_jumps",
        header=(
            "reference_date",
            "interpolation_method",
            "jump_index",
            "pillar_date",
            "left_forward_rate",
            "right_forward_rate",
            "jump_bp",
            "absolute_jump_bp",
        ),
        rows=jump_rows,
    )

    # --------------------------------------------------------------
    # Build human-readable report.
    # --------------------------------------------------------------

    report = TextReport()

    report.line(
        "F-TIIE Curve Diagnostics"
    )

    report.rule(
        character="=",
        width=74,
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
        f"Forward period       : "
        f"{FORWARD_PERIOD_DAYS} days"
    )

    report.line(
        f"Sampling grid        : "
        f"{GRID_STEP_DAYS} days"
    )

    report.line()

    # --------------------------------------------------------------
    # Sampled forward summary.
    # --------------------------------------------------------------

    report.line(
        "Sampled 28-Day Forward Curve"
    )

    report.rule(
        character="-",
        width=74,
    )

    report.line(
        f"Observations      : "
        f"{summary.observation_count}"
    )

    report.line(
        f"Minimum forward   : "
        f"{summary.minimum_rate:.6%} "
        f"at {summary.minimum_rate_date}"
    )

    report.line(
        f"Maximum forward   : "
        f"{summary.maximum_rate:.6%} "
        f"at {summary.maximum_rate_date}"
    )

    report.line(
        f"Mean forward      : "
        f"{summary.mean_rate:.6%}"
    )

    report.line(
        f"Std deviation     : "
        f"{summary.standard_deviation * 10_000:.4f} bp"
    )

    report.line(
        f"Max local change  : "
        f"{summary.maximum_local_change_bp:.4f} bp "
        f"at {summary.maximum_local_change_date}"
    )

    report.line()

    # --------------------------------------------------------------
    # Method-specific exact diagnostics.
    # --------------------------------------------------------------

    if log_linear is not None:
        report.line(
            "Log-Linear DF Segment Diagnostics"
        )

        report.rule(
            character="-",
            width=74,
        )

        report.line(
            f"Segments          : "
            f"{len(log_linear.segments)}"
        )

        report.line(
            f"Forward jumps     : "
            f"{len(log_linear.jumps)}"
        )

        report.line(
            f"Mean abs jump     : "
            f"{log_linear.mean_absolute_jump_bp:.4f} bp"
        )

        report.line(
            f"Max abs jump      : "
            f"{log_linear.maximum_absolute_jump_bp:.4f} bp"
        )

        report.line(
            f"Max jump date     : "
            f"{log_linear.maximum_absolute_jump_date}"
        )

        report.line()

        report.line(
            f"{'Pillar':>12} "
            f"{'Left Fwd':>12} "
            f"{'Right Fwd':>12} "
            f"{'Jump(bp)':>12}"
        )

        report.rule(
            character="-",
            width=52,
        )

        for jump in (
            log_linear.jumps
        ):
            report.line(
                f"{jump.pillar_date!s:>12} "
                f"{jump.left_forward_rate:>11.6%} "
                f"{jump.right_forward_rate:>11.6%} "
                f"{jump.jump_bp:>12.4f}"
            )

    else:
        report.line(
            "Method-Specific Segment Diagnostics"
        )

        report.rule(
            character="-",
            width=74,
        )

        report.line(
            "No log-linear-specific diagnostics "
            "are available for this curve."
        )

    report.line()

    report.save(
        section=REPORT_SECTION,
        stem="curve_diagnostics",
        echo=True,
    )


if __name__ == "__main__":
    main()