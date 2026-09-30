"""IO orchestration: capture sources before building a publishable baseline.

The envelope is issued only by this workflow, never by attaching sources to an
existing result. Value fingerprints detect inconsistent objects, not deliberate
Python object forgery or false caller declarations of market authenticity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import date, datetime, timezone
import hashlib
import json
import math
from uuid import uuid4

from .baseline import (
    BASELINE_IDENTIFIER, BASELINE_CALIBRATION_APPROACH, BASELINE_INTERPOLATION_METHOD,
    STANDARD_ACCEPTANCE_POLICY, BaselineConstructionPolicy, BaselineResult,
    build_baseline_ftiie_curve,
)
from .calendars import BusinessCalendar, CalendarProvenance
from .conventions import FTIIE_OIS_CONVENTIONS
from .inputs import PreparedBaselineInputs, prepare_baseline_inputs
from .quote_io import OISQuoteDataset, QuoteProvenance


def json_value(value):
    """Schema representation; exact binding floats already use hexadecimal strings."""
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    return value


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(json_value(value), sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def require_supported_policy(policy) -> None:
    """Validate supported V1 values; never supply missing historical identity."""
    supported = BaselineConstructionPolicy(
        BASELINE_IDENTIFIER, BASELINE_CALIBRATION_APPROACH,
        BASELINE_INTERPOLATION_METHOD, FTIIE_OIS_CONVENTIONS,
    )
    if json_value(policy) != json_value(supported):
        raise ValueError("Unsupported baseline policy identity.")


@dataclass(frozen=True, slots=True, init=False)
class ExecutionEnvelope:
    inputs: PreparedBaselineInputs
    quote_provenance: QuoteProvenance
    calendar_provenance: CalendarProvenance | None
    execution_id: str
    captured_at_utc: str
    result: BaselineResult
    binding_sha256: str

    def __init__(self, *args, **kwargs):
        raise TypeError("ExecutionEnvelope is issued by build_baseline_execution, not from a result.")

    def record(self) -> dict:
        return json_value({
            "execution_id": self.execution_id,
            "captured_at_utc": self.captured_at_utc,
            "inputs": self.inputs,
            "quote_provenance": self.quote_provenance,
            "calendar_provenance": self.calendar_provenance,
            "financial_context": self.result.financial_context,
            "acceptance": self.result.acceptance,
        })

    def validate(self) -> None:
        result = self.result
        acceptance = result.acceptance
        if not acceptance.is_standard_acceptance:
            raise ValueError("Standard publication rejects custom acceptance.")
        context = result.financial_context
        if context is None or context.inputs != self.inputs:
            raise ValueError("Execution inputs / financial context mismatch.")
        require_supported_policy(context.policy)
        if (not acceptance.is_bound_to(result.calibration_result, context)
                or acceptance.binding.evaluation_inputs != self.inputs
                or acceptance.acceptance_policy != STANDARD_ACCEPTANCE_POLICY):
            raise ValueError("Execution payload / acceptance binding mismatch.")
        if fingerprint(self.record()) != self.binding_sha256:
            raise ValueError("Execution provenance / context / acceptance binding mismatch.")


def build_baseline_execution(*, dataset: OISQuoteDataset, calendar: BusinessCalendar,
                             initial_discount_factors=None) -> ExecutionEnvelope:
    """Capture explicit source declarations and normalized values before the build.

    CSV adapters hash and parse the same bytes before entering this workflow.
    Sources are not reread at publication: a later file edit cannot rewrite history.
    In-memory sources may declare UNKNOWN with empty path/hash; calendar provenance
    may be absent. Neither a path nor a checksum authenticates a source.
    """
    execution_id = uuid4().hex
    captured_at = datetime.now(timezone.utc).isoformat()
    quote_provenance = replace(dataset.provenance)
    calendar_provenance = replace(calendar.provenance) if calendar.provenance else None
    inputs = prepare_baseline_inputs(quotes=dataset.quotes, calendar=calendar)
    result = build_baseline_ftiie_curve(
        quotes=inputs.quotes, calendar=inputs.calendar.to_calendar(),
        initial_discount_factors=initial_discount_factors,
    )
    envelope = object.__new__(ExecutionEnvelope)
    for name, value in dict(inputs=inputs, quote_provenance=quote_provenance,
                            calendar_provenance=calendar_provenance,
                            execution_id=execution_id, captured_at_utc=captured_at,
                            result=result).items():
        object.__setattr__(envelope, name, value)
    object.__setattr__(envelope, "binding_sha256", fingerprint(envelope.record()))
    envelope.validate()
    return envelope
