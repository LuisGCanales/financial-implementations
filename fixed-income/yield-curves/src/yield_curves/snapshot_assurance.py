"""Verify schema-3 binding and independently reprice, without solving or writing."""

import csv
import json
from datetime import date
from dataclasses import fields
from enum import Enum

from .baseline import (
    STANDARD_ACCEPTANCE_POLICY, BaselineConstructionPolicy, BaselineFinancialContext,
    BaselinePayloadBinding, assess_baseline_calibration,
)
from .calendars import BusinessCalendar, CalendarProvenance
from .calibration import GlobalCalibrationCheck, GlobalCalibrationResult
from .conventions import FTiieOISConventions
from .curves import CubicContinuousZeroCurve, CurveInterpolationMethod
from .execution import fingerprint, json_value, require_supported_policy
from .inputs import prepare_baseline_inputs
from .quote_io import QuoteProvenance, read_ois_quotes_csv
from .snapshots import resolve_current_snapshot


def _require_equal(actual, expected, label):
    if json_value(actual) != json_value(expected):
        raise ValueError(f"Snapshot {label} binding mismatch.")


def assess_current_snapshot(output_root):
    """Verify historical V1 identity and reprice under that same supported policy.

    No solver, publication or writes. No implicit policy reevaluation: other
    policy identities and old unbound schemas fail explicitly. Historical
    acceptance stays in the artifact; the return value is a fresh assessment.
    Checksums/fingerprints are integrity checks, not source authentication.
    """
    run = resolve_current_snapshot(output_root)
    metadata = json.loads((run / "metadata.json").read_text())
    execution = metadata["execution"]
    historical = execution["acceptance"]
    context_data = execution["financial_context"]
    require_supported_policy(context_data["policy"])
    _require_equal(historical["acceptance_policy"], STANDARD_ACCEPTANCE_POLICY,
                   "standard acceptance policy")
    _require_equal(metadata["acceptance"], historical, "historical acceptance")
    _require_equal(metadata["quote_provenance"], execution["quote_provenance"], "source provenance")
    # Validate declared provenance shape/classification, without reading source files.
    QuoteProvenance(**execution["quote_provenance"])
    if (len(execution["execution_id"]) != 32
            or any(c not in "0123456789abcdef" for c in execution["execution_id"])):
        raise ValueError("Invalid execution identity.")
    for field, value in (("financial_context_sha256", context_data),
                         ("acceptance_sha256", historical),
                         ("payload_sha256", historical["binding"])):
        _require_equal(metadata[field], fingerprint(value), field)

    quotes = read_ois_quotes_csv(run / "input_quotes.csv")
    data = json.loads((run / "calendar.json").read_text())
    _require_equal(data["provenance"], execution["calendar_provenance"], "calendar provenance")
    calendar = BusinessCalendar(
        name=data["name"], holidays=frozenset(map(date.fromisoformat, data["holidays"])),
        weekend_days=frozenset(data["weekend_days"]),
        coverage_start=date.fromisoformat(data["coverage_start"]),
        coverage_end=date.fromisoformat(data["coverage_end"]),
        provenance=CalendarProvenance(**data["provenance"]) if data["provenance"] else None,
    )
    prepared = prepare_baseline_inputs(quotes=quotes, calendar=calendar)
    _require_equal(prepared, execution["inputs"], "normalized input")
    _require_equal(prepared, context_data["inputs"], "financial context input")
    # Decode the supported historical policy, rather than fill absent identities.
    policy_data = dict(context_data["policy"])
    policy_data["interpolation_method"] = CurveInterpolationMethod(policy_data["interpolation_method"])
    convention_data = dict(policy_data["conventions"])
    for field in fields(FTiieOISConventions):
        if isinstance(field.default, Enum):
            convention_data[field.name] = type(field.default)(convention_data[field.name])
    policy_data["conventions"] = FTiieOISConventions(**convention_data)
    policy_data["acceptance_policy"] = STANDARD_ACCEPTANCE_POLICY
    policy = BaselineConstructionPolicy(**policy_data)
    context = BaselineFinancialContext(prepared, policy)
    for field, value in (("baseline_identifier", policy.baseline_identifier),
                         ("calibration_approach", policy.calibration_approach),
                         ("interpolation_method", policy.interpolation_method),
                         ("projection_discount_assumption", policy.projection_discounting)):
        _require_equal(metadata[field], value, field)

    with (run / "curve_nodes.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    _require_equal([row["tenor"] for row in rows], [q.tenor for q in quotes], "node ordering")
    _require_equal(metadata["quote_count"], len(quotes), "quote count")
    _require_equal(metadata["node_count"], len(rows), "node count")
    curve = CubicContinuousZeroCurve(
        reference_date=date.fromisoformat(metadata["curve_reference_date"]),
        node_dates=tuple(date.fromisoformat(row["pillar_date"]) for row in rows),
        discount_factors=tuple(float(row["discount_factor"]) for row in rows),
    )
    for row, day in zip(rows, curve.node_dates, strict=True):
        _require_equal(float(row["continuous_zero_rate"]), curve.zero_rate(day), "node zero rate")
    # The binding preserves original solver checks and diagnostics exactly, including
    # nonfinite hex values. Acceptance checks are independent and are not solver data.
    state = historical["binding"]["calibration_state"]
    checks = tuple(GlobalCalibrationCheck(c[0], *(float.fromhex(v) for v in c[1:]))
                   for c in state[1])
    calibration = GlobalCalibrationResult(
        curve=curve, interpolation_method=policy.interpolation_method, checks=checks,
        success=state[0], message=state[2], function_evaluations=state[3],
        jacobian_evaluations=state[4], cost=float.fromhex(state[5]),
        optimality=float.fromhex(state[6]), max_abs_repricing_error_bp=float.fromhex(state[7]),
        rmse_repricing_error_bp=float.fromhex(state[8]),
    )
    _require_equal(metadata["solver"], {key: getattr(calibration, key) for key in (
        "success", "message", "function_evaluations", "jacobian_evaluations", "cost", "optimality",
    )}, "solver declarations")
    binding = BaselinePayloadBinding.capture(calibration, prepared, context, policy.acceptance_policy)
    _require_equal(binding, historical["binding"], "curve / payload / acceptance")
    assessment = assess_baseline_calibration(calibration_result=calibration, quotes=quotes,
                                             calendar=calendar)
    # This compares fresh pricing with the historical assessment; it never replaces it.
    actual = json_value(assessment)
    _require_equal({k: v for k, v in actual.items() if k != "binding"},
                   {k: v for k, v in historical.items() if k != "binding"},
                   "independent repricing / historical acceptance")
    with (run / "quote_repricing.csv").open(newline="") as file:
        repricing = list(csv.DictReader(file))
    expected = [{"tenor": c.tenor, "input_quote": str(c.market_quote),
                 "repriced_quote": str(c.model_quote), "error_bp": str(c.error_bp),
                 "status": c.status.value} for c in assessment.checks]
    _require_equal(repricing, expected, "repricing artifact")
    return assessment
