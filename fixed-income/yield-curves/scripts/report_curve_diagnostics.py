"""Report curve-shape diagnostics for the canonical synthetic bootstrap."""

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

    curve = bootstrap_result.curve

    diagnostics = analyze_curve(
        curve=curve,
        last_supported_date=(
            curve.last_node_date
        ),
        forward_period_days=28,
        grid_step_days=7,
    )

    summary = (
        diagnostics.forward_summary
    )

    print(
        "F-TIIE Curve Diagnostics"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Sampled 28-Day Forward Curve"
    )

    print(
        f"Observations      : "
        f"{summary.observation_count}"
    )

    print(
        f"Minimum forward   : "
        f"{summary.minimum_rate:.6%} "
        f"at {summary.minimum_rate_date}"
    )

    print(
        f"Maximum forward   : "
        f"{summary.maximum_rate:.6%} "
        f"at {summary.maximum_rate_date}"
    )

    print(
        f"Mean forward      : "
        f"{summary.mean_rate:.6%}"
    )

    print(
        f"Std deviation     : "
        f"{summary.standard_deviation * 10_000:.4f} bp"
    )

    print(
        f"Max local change  : "
        f"{summary.maximum_local_change_bp:.4f} bp "
        f"at {summary.maximum_local_change_date}"
    )

    print()

    if diagnostics.log_linear is not None:
        log_linear = (
            diagnostics.log_linear
        )

        print(
            "Log-Linear DF Segment Diagnostics"
        )

        print(
            f"Segments          : "
            f"{len(log_linear.segments)}"
        )

        print(
            f"Forward jumps     : "
            f"{len(log_linear.jumps)}"
        )

        print(
            f"Mean abs jump     : "
            f"{log_linear.mean_absolute_jump_bp:.4f} bp"
        )

        print(
            f"Max abs jump      : "
            f"{log_linear.maximum_absolute_jump_bp:.4f} bp"
        )

        print(
            f"Max jump date     : "
            f"{log_linear.maximum_absolute_jump_date}"
        )

        print()
        print(
            f"{'Pillar':>12} "
            f"{'Left Fwd':>12} "
            f"{'Right Fwd':>12} "
            f"{'Jump(bp)':>12}"
        )

        print(
            "-" * 52
        )

        for jump in log_linear.jumps:
            print(
                f"{jump.pillar_date!s:>12} "
                f"{jump.left_forward_rate:>11.6%} "
                f"{jump.right_forward_rate:>11.6%} "
                f"{jump.jump_bp:>12.4f}"
            )


if __name__ == "__main__":
    main()