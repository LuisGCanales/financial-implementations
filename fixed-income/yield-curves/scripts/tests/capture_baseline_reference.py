"""Capture a candidate numerical regression reference for human review.

Run explicitly with a new output path; an existing reference is never replaced.
This exercises the Python API without publishing an operational snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import numpy
import scipy

from yield_curves.baseline import BASELINE_IDENTIFIER, build_baseline_ftiie_curve
from yield_curves.research.calendars import build_projected_mxmc_calendar
from yield_curves.research.synthetic import read_synthetic_ois_quotes_csv
from yield_curves.tooling.project_paths import find_project_root
from yield_curves.tooling.reference_candidates import validate_candidate_path, write_candidate


def capture_reference(root: Path) -> str:
    """Run the public baseline API and serialize the v1 numerical test contract."""
    quote_path = root / "data/synthetic/ftiie_ois_quotes_v1.csv"
    quotes = read_synthetic_ois_quotes_csv(quote_path)
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2057)
    result = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)
    if not result.accepted_for_use:
        raise RuntimeError(f"Baseline was rejected: {result.acceptance.issues}")

    curve = result.curve
    nodes = [
        {
            "date": day.isoformat(),
            "discount_factor": df,
            "zero_rate": curve.zero_rate(day),
        }
        for day, df in zip(curve.node_dates, curve.discount_factors, strict=True)
    ]
    # One interior observation in every segment also protects interpolation.
    observations = []
    left = curve.reference_date
    for right in curve.node_dates:
        day = left + (right - left) // 2
        end = min(day + timedelta(days=28), curve.node_dates[-1])
        observations.append({
            "date": day.isoformat(),
            "discount_factor": curve.discount_factor(day),
            "zero_rate": curve.zero_rate(day),
            "forward_end_date": end.isoformat(),
            "forward_rate": curve.forward_rate(day, end),
        })
        left = right

    holiday_bytes = "\n".join(
        sorted(day.isoformat() for day in calendar.holidays)
    ).encode("utf-8")
    reference = {
        "schema_version": 1,
        "purpose": "Numerical regression candidate; not synthetic known truth",
        "baseline_identifier": BASELINE_IDENTIFIER,
        "environment": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
        },
        "inputs": {
            "quotes_path": quote_path.relative_to(root).as_posix(),
            "quotes_sha256": hashlib.sha256(quote_path.read_bytes()).hexdigest(),
            "quote_count": len(quotes),
            "calendar": {
                "name": calendar.name,
                "start_year": 2026,
                "end_year": 2057,
                "weekend_days": sorted(calendar.weekend_days),
                "holidays_sha256": hashlib.sha256(holiday_bytes).hexdigest(),
            },
            "initial_discount_factors": None,
        },
        "reference_date": curve.reference_date.isoformat(),
        "interpolation_method": result.calibration_result.interpolation_method.value,
        # Keep the v1 numerical contract; do not serialize live payload binding.
        "acceptance": {
            "calibration_success": result.acceptance.calibration_success,
            "accepted_for_use": result.acceptance.accepted_for_use,
            "structural_valid": result.acceptance.structural_valid,
            "checks": [asdict(check) for check in result.acceptance.checks],
            "issues": result.acceptance.issues,
            "pass_tolerance_bp": result.acceptance.pass_tolerance_bp,
            "max_abs_repricing_error_bp": result.acceptance.max_abs_repricing_error_bp,
        },
        "nodes": nodes,
        "interior_observations": observations,
    }
    return json.dumps(reference, indent=2, allow_nan=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="New candidate JSON path; existing files are rejected.")
    args = parser.parse_args()
    root = find_project_root(Path(__file__))
    try:
        validate_candidate_path(args.output, root=root)
    except ValueError as error:
        parser.error(str(error))
    payload = capture_reference(root)
    write_candidate(args.output, payload.encode("utf-8"), root=root)
    print(f"Candidate written to {args.output}; review before any manual fixture update.")


if __name__ == "__main__":
    main()
