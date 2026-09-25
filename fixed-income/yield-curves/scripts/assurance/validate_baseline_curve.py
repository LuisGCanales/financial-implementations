"""Validate the current cubic simultaneous F-TIIE baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from yield_curves.baseline import (
    BASELINE_INTERPOLATION_METHOD,
    build_baseline_ftiie_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.project_paths import find_project_root
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = find_project_root(Path(__file__))
DEFAULT_QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


def _parse_args(arguments: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Validate the current cubic simultaneous F-TIIE baseline."
    )
    parser.add_argument(
        "--quotes",
        type=Path,
        default=DEFAULT_QUOTES_PATH,
        help="Path to a quote CSV input.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parse_args(arguments)
    quotes = read_synthetic_ois_quotes_csv(args.quotes.resolve())
    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )
    result = build_baseline_ftiie_curve(
        quotes=quotes,
        calendar=calendar,
    )

    acceptance = result.acceptance
    print(f"solver_success: {acceptance.calibration_success}")
    print(f"accepted_for_use: {acceptance.accepted_for_use}")
    print(f"quote_count: {len(acceptance.checks)}")
    print(
        "max_abs_repricing_error_bp: "
        f"{acceptance.max_abs_repricing_error_bp:.12g}"
    )
    print(f"failed_or_review_checks: ")

    non_pass_checks = [
        check.tenor
        for check in acceptance.checks
        if check.status.value != "PASS"
    ]
    print(", ".join(non_pass_checks) or "none")
    print(
        "interpolation_method: "
        f"{BASELINE_INTERPOLATION_METHOD.value}"
    )

    if acceptance.issues:
        print("issues:")
        for issue in acceptance.issues:
            print(f"- {issue}")

    return 0 if acceptance.accepted_for_use else 1


if __name__ == "__main__":
    raise SystemExit(main())