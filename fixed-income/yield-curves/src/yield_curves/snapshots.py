"""Per-run baseline artifacts and atomic publication of an accepted snapshot."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from importlib.metadata import version
from itertools import zip_longest
from pathlib import Path
from uuid import uuid4

from .baseline import BASELINE_IDENTIFIER, BASELINE_CALIBRATION_APPROACH, BaselineResult
from .calendars import BusinessCalendar
from .quote_io import OISQuoteDataset


SCHEMA_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class SnapshotExport:
    run_id: str
    run_path: Path
    published: bool


def _safe(value):
    """JSON null / CSV blank represents unavailable or non-finite diagnostics."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as file:
        json.dump(_safe(value), file, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def _write_csv(path: Path, header, rows) -> None:
    with path.open("x", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(_safe(row) for row in rows)
        file.flush()
        os.fsync(file.fileno())


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def export_baseline_snapshot(
    *, result: BaselineResult, dataset: OISQuoteDataset,
    calendar: BusinessCalendar, output_root: str | Path,
) -> SnapshotExport:
    """Archive a run and publish it only when operational acceptance passed.

    Supply the dataset/calendar used for this result. No input files are reread.
    Run files are immutable by convention. Concurrent accepted publishers use
    last-completed-pointer-replacement wins, not valuation-date ordering.
    """
    calibration = result.calibration_result
    acceptance = result.acceptance
    curve = result.curve
    if result.accepted_for_use:
        if not (calibration.success and acceptance.calibration_success
                and acceptance.structural_valid and curve is not None
                and not acceptance.issues and acceptance.checks
                and math.isfinite(acceptance.pass_tolerance_bp)
                and acceptance.pass_tolerance_bp >= 0
                and all(check.status.value == "PASS"
                        and math.isfinite(check.absolute_error_bp)
                        and check.absolute_error_bp <= acceptance.pass_tolerance_bp
                        for check in acceptance.checks)):
            raise ValueError("Inconsistent accepted result cannot be published.")
        if [(q.tenor, q.par_rate) for q in dataset.quotes] != [
            (check.tenor, check.market_quote) for check in acceptance.checks
        ]:
            raise ValueError("Dataset does not match the accepted repricing checks.")

    root = Path(output_root).resolve()
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    run_id = uuid4().hex
    destination = runs / run_id
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=runs))
    pointer_temp = root / f".current-{run_id}.tmp"
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        _write_csv(staging / "input_quotes.csv",
                   ("tenor", "trade_date", "contractual_maturity_date", "par_rate"),
                   ((q.tenor, q.trade_date, q.contractual_maturity_date, q.par_rate)
                    for q in dataset.quotes))
        calendar_data = {
            "name": calendar.name,
            "coverage_start": calendar.coverage_start,
            "coverage_end": calendar.coverage_end,
            "weekend_days": sorted(calendar.weekend_days),
            "holidays": sorted(calendar.holidays),
            "provenance": asdict(calendar.provenance) if calendar.provenance else None,
        }
        _write_json(staging / "calendar.json", calendar_data)
        node_rows = []
        for index, (day, df) in enumerate(zip_longest(
            getattr(curve, "node_dates", ()), getattr(curve, "discount_factors", ())
        )):
            tenor = dataset.quotes[index].tenor if index < len(dataset.quotes) else None
            zero = curve.zero_rate(day) if acceptance.structural_valid and day is not None else None
            node_rows.append((tenor, day, df, zero))
        _write_csv(staging / "curve_nodes.csv",
                   ("tenor", "pillar_date", "discount_factor", "continuous_zero_rate"), node_rows)
        _write_csv(staging / "quote_repricing.csv",
                   ("tenor", "input_quote", "repriced_quote", "error_bp", "status"),
                   ((c.tenor, c.market_quote, c.model_quote, c.error_bp, c.status.value)
                    for c in acceptance.checks))
        metadata = {
            "artifact_schema_version": SCHEMA_VERSION,
            "run_id": run_id, "created_at_utc": created_at,
            "baseline_identifier": BASELINE_IDENTIFIER,
            "calibration_approach": BASELINE_CALIBRATION_APPROACH,
            "interpolation_method": calibration.interpolation_method.value,
            "projection_discount_assumption": "same_curve",
            "curve_reference_date": getattr(curve, "reference_date", None),
            "quote_count": len(dataset.quotes), "node_count": len(node_rows),
            "quote_provenance": asdict(dataset.provenance),
            "acceptance": asdict(acceptance),
            "solver": {key: getattr(calibration, key) for key in (
                "success", "message", "function_evaluations", "jacobian_evaluations",
                "cost", "optimality",
            )},
            "environment": {"python": platform.python_version(),
                            "numpy": version("numpy"), "scipy": version("scipy"),
                            "yield_curves": version("yield-curves")},
            "non_finite_encoding": "JSON null; CSV blank",
        }
        _write_json(staging / "metadata.json", metadata)
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted(staging.iterdir())}
        manifest = {
            "artifact_schema_version": SCHEMA_VERSION, "run_id": run_id,
            "created_at_utc": created_at, "accepted_for_use": result.accepted_for_use,
            "files_sha256": hashes,
        }
        _write_json(staging / "manifest.json", manifest)
        _sync_directory(staging)
        # Staging and destination share a filesystem. No published pointer can
        # refer to this run until the complete directory has been renamed.
        staging.rename(destination)
        _sync_directory(runs)
        if result.accepted_for_use:
            _write_json(pointer_temp, {
                "artifact_schema_version": SCHEMA_VERSION, "run_id": run_id,
                "run_path": f"runs/{run_id}",
                "manifest_sha256": hashlib.sha256(
                    (destination / "manifest.json").read_bytes()
                ).hexdigest(),
            })
            os.replace(pointer_temp, root / "current.json")
            _sync_directory(root)
        return SnapshotExport(run_id, destination, result.accepted_for_use)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        pointer_temp.unlink(missing_ok=True)


def resolve_current_snapshot(output_root: str | Path) -> Path:
    """Read the pointer once and verify the complete run before returning its path."""
    root = Path(output_root).resolve()
    pointer = json.loads((root / "current.json").read_text(encoding="utf-8"))
    run_id = pointer["run_id"]
    if (pointer["artifact_schema_version"] != SCHEMA_VERSION
            or not isinstance(run_id, str) or len(run_id) != 32
            or any(c not in "0123456789abcdef" for c in run_id)
            or pointer["run_path"] != f"runs/{run_id}"):
        raise ValueError("Invalid snapshot pointer.")
    run = root / "runs" / run_id
    raw_manifest = (run / "manifest.json").read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != pointer["manifest_sha256"]:
        raise ValueError("Snapshot manifest checksum mismatch.")
    manifest = json.loads(raw_manifest)
    expected_files = {"metadata.json", "calendar.json", "input_quotes.csv",
                      "curve_nodes.csv", "quote_repricing.csv"}
    if (manifest["run_id"] != run_id or manifest["accepted_for_use"] is not True
            or manifest["artifact_schema_version"] != SCHEMA_VERSION
            or set(manifest["files_sha256"]) != expected_files):
        raise ValueError("Invalid snapshot manifest.")
    for name, checksum in manifest["files_sha256"].items():
        if hashlib.sha256((run / name).read_bytes()).hexdigest() != checksum:
            raise ValueError(f"Snapshot checksum mismatch: {name}")
    metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
    if metadata["run_id"] != run_id or metadata["acceptance"]["accepted_for_use"] is not True:
        raise ValueError("Snapshot metadata does not describe an accepted run.")
    return run
