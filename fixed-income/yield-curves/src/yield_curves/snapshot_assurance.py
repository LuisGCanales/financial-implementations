"""Reassess a persisted accepted baseline without rerunning calibration."""

import csv
import json
from datetime import date

from .baseline import (BASELINE_IDENTIFIER, BASELINE_CALIBRATION_APPROACH,
                       BASELINE_INTERPOLATION_METHOD, assess_baseline_calibration)
from .calendars import BusinessCalendar, CalendarProvenance
from .calibration import GlobalCalibrationCheck, GlobalCalibrationResult
from .curves import CubicContinuousZeroCurve
from .quote_io import read_ois_quotes_csv
from .snapshots import resolve_current_snapshot


def assess_current_snapshot(output_root):
    """Verify hashes and reprice persisted nodes under the current baseline policy.

    Solver diagnostics are historical declarations, not a newly executed solve.
    Checksums provide integrity checking, not source authentication.
    """
    run = resolve_current_snapshot(output_root)
    metadata = json.loads((run / "metadata.json").read_text())
    if (metadata["baseline_identifier"] != BASELINE_IDENTIFIER
            or metadata["calibration_approach"] != BASELINE_CALIBRATION_APPROACH
            or metadata["interpolation_method"] != BASELINE_INTERPOLATION_METHOD.value
            or metadata["projection_discount_assumption"] != "same_curve"):
        raise ValueError("Snapshot does not describe the supported baseline.")
    quotes = read_ois_quotes_csv(run / "input_quotes.csv")
    data = json.loads((run / "calendar.json").read_text())
    calendar = BusinessCalendar(
        name=data["name"], holidays=frozenset(map(date.fromisoformat, data["holidays"])),
        weekend_days=frozenset(data["weekend_days"]),
        coverage_start=date.fromisoformat(data["coverage_start"]),
        coverage_end=date.fromisoformat(data["coverage_end"]),
        provenance=CalendarProvenance(**data["provenance"]) if data["provenance"] else None,
    )
    with (run / "curve_nodes.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    if [row["tenor"] for row in rows] != [q.tenor for q in quotes]:
        raise ValueError("Snapshot node ordering does not match input quotes.")
    if metadata["quote_count"] != len(quotes) or metadata["node_count"] != len(rows):
        raise ValueError("Snapshot counts do not match its payloads.")
    curve = CubicContinuousZeroCurve(
        reference_date=date.fromisoformat(metadata["curve_reference_date"]),
        node_dates=tuple(date.fromisoformat(row["pillar_date"]) for row in rows),
        discount_factors=tuple(float(row["discount_factor"]) for row in rows),
    )
    checks = tuple(GlobalCalibrationCheck(
        tenor=c["tenor"], market_quote=c["market_quote"], model_quote=c["model_quote"],
        error_bp=c["error_bp"],
    ) for c in metadata["acceptance"]["checks"])
    calibration = GlobalCalibrationResult(
        curve=curve, interpolation_method=BASELINE_INTERPOLATION_METHOD, checks=checks,
        **metadata["solver"], max_abs_repricing_error_bp=float("inf"),
        rmse_repricing_error_bp=float("inf"),
    )
    return assess_baseline_calibration(calibration_result=calibration, quotes=quotes,
                                       calendar=calendar)
