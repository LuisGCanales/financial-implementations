"""Build the current operational F-TIIE baseline snapshot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Sequence

from yield_curves.baseline import (
    BASELINE_CALIBRATION_APPROACH,
    BASELINE_FAIL_TOLERANCE_BP,
    BASELINE_IDENTIFIER,
    BASELINE_INTERPOLATION_METHOD,
    BASELINE_PASS_TOLERANCE_BP,
    BaselineResult,
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
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "baseline"
CALENDAR_START_YEAR = 2026
CALENDAR_END_YEAR = 2057


def _project_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _write_curve_nodes(
    *,
    result: BaselineResult,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            (
                "tenor",
                "pillar_date",
                "discount_factor",
                "continuous_zero_rate",
            )
        )

        for index, check in enumerate(
            result.calibration_result.checks
        ):
            node_date = result.curve.node_dates[index]
            writer.writerow(
                (
                    check.tenor,
                    node_date.isoformat(),
                    result.curve.discount_factors[index],
                    result.curve.zero_rate(node_date),
                )
            )


def _write_quote_repricing(
    *,
    result: BaselineResult,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            (
                "tenor",
                "pillar_date",
                "input_quote",
                "repriced_quote",
                "error_bp",
                "status",
            )
        )

        for index, check in enumerate(result.acceptance.checks):
            writer.writerow(
                (
                    check.tenor,
                    result.curve.node_dates[index].isoformat(),
                    check.market_quote,
                    check.model_quote,
                    check.error_bp,
                    check.status.value,
                )
            )


def _write_metadata(
    *,
    result: BaselineResult,
    quotes_path: Path,
    calendar_name: str,
    calendar_holiday_count: int,
    path: Path,
) -> None:
    acceptance = result.acceptance
    calibration = result.calibration_result

    metadata = {
        "artifact_schema_version": "1.0",
        "baseline_identifier": BASELINE_IDENTIFIER,
        "source_quote_path": _project_relative_path(quotes_path),
        "source_classification": (
            "SYNTHETIC_REFERENCE_DATA"
            if quotes_path.resolve() == DEFAULT_QUOTES_PATH.resolve()
            else "USER_PROVIDED_QUOTE_DATA"
        ),
        "curve_reference_date": (
            result.curve.reference_date.isoformat()
        ),
        "interpolation_method": BASELINE_INTERPOLATION_METHOD.value,
        "calibration_approach": BASELINE_CALIBRATION_APPROACH,
        "projection_discount_assumption": "same_curve",
        "node_count": len(result.curve.node_dates),
        "quote_count": len(acceptance.checks),
        "solver_success": calibration.success,
        "accepted_for_use": acceptance.accepted_for_use,
        "repricing_tolerance": {
            "pass_tolerance_bp": acceptance.pass_tolerance_bp,
            "fail_tolerance_bp": BASELINE_FAIL_TOLERANCE_BP,
        },
        "max_abs_repricing_error_bp": (
            acceptance.max_abs_repricing_error_bp
        ),
        "calendar": {
            "name": calendar_name,
            "holiday_count": calendar_holiday_count,
            "coverage": (
                f"projected {CALENDAR_START_YEAR}-"
                f"{CALENDAR_END_YEAR}"
            ),
        },
        "solver": {
            "message": calibration.message,
            "function_evaluations": calibration.function_evaluations,
            "jacobian_evaluations": calibration.jacobian_evaluations,
            "cost": calibration.cost,
            "optimality": calibration.optimality,
        },
        "acceptance_issues": acceptance.issues,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_snapshot(
    *,
    quotes_path: Path = DEFAULT_QUOTES_PATH,
    output_root: Path = OUTPUT_ROOT,
) -> BaselineResult:
    """Build the baseline and persist its operational snapshot."""

    quotes = read_synthetic_ois_quotes_csv(quotes_path)
    calendar = build_projected_mxmc_calendar(
        start_year=CALENDAR_START_YEAR,
        end_year=CALENDAR_END_YEAR,
    )
    result = build_baseline_ftiie_curve(
        quotes=quotes,
        calendar=calendar,
    )

    _write_curve_nodes(
        result=result,
        path=output_root / "curve_nodes.csv",
    )
    _write_quote_repricing(
        result=result,
        path=output_root / "quote_repricing.csv",
    )
    _write_metadata(
        result=result,
        quotes_path=quotes_path,
        calendar_name=calendar.name,
        calendar_holiday_count=len(calendar.holidays),
        path=output_root / "metadata.json",
    )

    return result


def _parse_args(arguments: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Build the current cubic simultaneous F-TIIE baseline."
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
    result = build_snapshot(quotes_path=args.quotes.resolve())
    calibration = result.calibration_result
    acceptance = result.acceptance

    print(f"solver_success: {calibration.success}")
    print(f"accepted_for_use: {acceptance.accepted_for_use}")
    print(f"quote_count: {len(acceptance.checks)}")
    print(
        "max_abs_repricing_error_bp: "
        f"{acceptance.max_abs_repricing_error_bp:.12g}"
    )
    print(f"node_count: {len(result.curve.node_dates)}")
    print(
        "interpolation_method: "
        f"{BASELINE_INTERPOLATION_METHOD.value}"
    )
    print(f"output_root: {_project_relative_path(OUTPUT_ROOT)}")

    return 0 if acceptance.accepted_for_use else 1


if __name__ == "__main__":
    raise SystemExit(main())