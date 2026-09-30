"""Stable policy boundary for the current F-TIIE curve baseline."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum, StrEnum
from math import isfinite
from typing import Sequence

from .quotes import OISCalibrationQuote
from .calendars import BusinessCalendar, CalendarCoverageError
from .calibration import (
    GlobalCalibrationResult,
    calibrate_ftiie_ois_curve_simultaneously,
)
from .conventions import FTiieOISConventions, FTIIE_OIS_CONVENTIONS
from .curves import CurveInterpolationMethod, CubicContinuousZeroCurve
from .inputs import BaselineInputError, PreparedBaselineInputs, prepare_baseline_inputs
from .repricing import (
    InstrumentRepricingCheck,
    InstrumentValidationStatus,
    reprice_calibration_instruments,
)


BASELINE_INTERPOLATION_METHOD = (
    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
)
BASELINE_CALIBRATION_APPROACH = (
    "simultaneous_nodal_calibration"
)
BASELINE_IDENTIFIER = "FTIIE_CUBIC_SIMULTANEOUS_V1"
BASELINE_PASS_TOLERANCE_BP = 0.01
BASELINE_FAIL_TOLERANCE_BP = 0.10


class AcceptanceKind(StrEnum):
    STANDARD_BASELINE_ACCEPTANCE = "STANDARD_BASELINE_ACCEPTANCE"
    CUSTOM_ANALYTICAL_ASSESSMENT = "CUSTOM_ANALYTICAL_ASSESSMENT"


@dataclass(frozen=True, slots=True)
class AcceptancePolicy:
    """Captured rule identity and effective tolerances; not publication authority."""

    kind: AcceptanceKind
    identifier: str | None
    pass_tolerance_bp: float
    fail_tolerance_bp: float


# Names the existing V1 rules: successful solver, valid structure/geometry,
# nonempty finite independent repricing, and every check PASS. REVIEW rejects.
STANDARD_ACCEPTANCE_POLICY = AcceptancePolicy(
    AcceptanceKind.STANDARD_BASELINE_ACCEPTANCE,
    "FTIIE_STANDARD_BASELINE_ACCEPTANCE_V1",
    BASELINE_PASS_TOLERANCE_BP,
    BASELINE_FAIL_TOLERANCE_BP,
)


class _OmittedTolerance(Enum):
    OMITTED = "omitted"


@dataclass(frozen=True, slots=True)
class BaselineConstructionPolicy:
    """Financial policy selected at build time, including standard acceptance."""

    baseline_identifier: str
    calibration_approach: str
    interpolation_method: CurveInterpolationMethod
    conventions: FTiieOISConventions
    instrument: str = "FTIIE_OIS"
    profile: str = "Core-v1"
    projection_discounting: str = "same_curve"
    reference_date_rule: str = "common_effective_date"
    pillar_date_rule: str = "final_payment_date"
    spline_boundary: str = "natural"
    zero_at_origin: str = "first_nodal_zero"
    extrapolation: bool = False
    acceptance_policy: AcceptancePolicy = STANDARD_ACCEPTANCE_POLICY


@dataclass(frozen=True, slots=True)
class BaselineFinancialContext:
    """Captured construction inputs and selected policy, without source provenance."""

    inputs: PreparedBaselineInputs
    policy: BaselineConstructionPolicy


@dataclass(frozen=True, slots=True)
class BaselinePayloadBinding:
    """Exact value identity of the assessed payload, including mutable spline state.

    Hexadecimal floats preserve binary values without repricing tolerances or
    rounding. Nonfinite diagnostic values remain explicit (nan/inf). This is
    value binding, not authentication against deliberate object forgery.
    """

    evaluation_inputs: PreparedBaselineInputs | None
    financial_context: BaselineFinancialContext | None
    interpolation_method: str
    curve_type: tuple[str, str]
    reference_date: date | None
    node_dates: tuple[date, ...]
    discount_factors: tuple[str, ...]
    spline_state: tuple
    calibration_state: tuple
    acceptance_policy: AcceptancePolicy | None = None

    @classmethod
    def capture(
        cls, result: GlobalCalibrationResult,
        inputs: PreparedBaselineInputs | None,
        context: BaselineFinancialContext | None,
        acceptance_policy: AcceptancePolicy | None = None,
    ) -> "BaselinePayloadBinding":
        curve = result.curve
        spline_state = ()
        if isinstance(curve, CubicContinuousZeroCurve):
            spline = curve._spline_object
            spline_state = (
                tuple(spline.x.shape), tuple(float(x).hex() for x in spline.x.flat),
                tuple(spline.c.shape), tuple(float(x).hex() for x in spline.c.flat),
                spline.extrapolate, spline.axis,
            )
        checks = tuple(
            (c.tenor, float(c.market_quote).hex(), float(c.model_quote).hex(),
             float(c.error_bp).hex()) for c in result.checks
        )
        return cls(
            inputs, context, str(result.interpolation_method),
            (type(curve).__module__, type(curve).__qualname__),
            getattr(curve, "reference_date", None),
            tuple(getattr(curve, "node_dates", ())),
            tuple(float(df).hex() for df in getattr(curve, "discount_factors", ())),
            spline_state,
            (result.success, checks, result.message, result.function_evaluations,
             result.jacobian_evaluations, float(result.cost).hex(),
             float(result.optimality).hex(),
             float(result.max_abs_repricing_error_bp).hex(),
             float(result.rmse_repricing_error_bp).hex()),
            acceptance_policy,
        )


@dataclass(frozen=True, slots=True)
class BaselineAcceptance:
    """Historical assessment of the payload recorded in ``binding``."""

    calibration_success: bool
    accepted_for_use: bool
    structural_valid: bool

    checks: tuple[
        InstrumentRepricingCheck,
        ...,
    ]
    issues: tuple[str, ...]

    pass_tolerance_bp: float
    max_abs_repricing_error_bp: float
    fail_tolerance_bp: float = BASELINE_FAIL_TOLERANCE_BP
    binding: BaselinePayloadBinding | None = None
    acceptance_policy: AcceptancePolicy | None = None

    @property
    def is_standard_acceptance(self) -> bool:
        """Identify standard rules, without certifying build history/publication."""
        return self.acceptance_policy == STANDARD_ACCEPTANCE_POLICY

    def is_bound_to(
        self, calibration_result: GlobalCalibrationResult,
        financial_context: BaselineFinancialContext | None = None,
    ) -> bool:
        """Check current payload values; a standalone assessment has no build history."""
        if self.binding is None:
            return False
        if self.acceptance_policy is not None and (
            self.pass_tolerance_bp != self.acceptance_policy.pass_tolerance_bp
            or self.fail_tolerance_bp != self.acceptance_policy.fail_tolerance_bp
        ):
            return False
        try:
            return self.binding == BaselinePayloadBinding.capture(
                calibration_result, self.binding.evaluation_inputs, financial_context,
                self.acceptance_policy,
            )
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            return False


@dataclass(frozen=True, slots=True)
class BaselineResult:
    """Calibration and historical acceptance with a checked financial value binding."""

    calibration_result: GlobalCalibrationResult
    acceptance: BaselineAcceptance
    financial_context: BaselineFinancialContext | None = None

    def __post_init__(self) -> None:
        if not self.acceptance.is_bound_to(self.calibration_result, self.financial_context):
            raise ValueError("Acceptance payload binding mismatch.")

    @property
    def curve(self):
        """Return the calibrated baseline curve."""

        return self.calibration_result.curve

    @property
    def accepted_for_use(self) -> bool:
        """Require both historical acceptance and an unchanged current payload."""

        return self.acceptance.accepted_for_use and self.acceptance.is_bound_to(
            self.calibration_result, self.financial_context
        )


def _independently_reprice(
    *,
    calibration_result: GlobalCalibrationResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float,
    fail_tolerance_bp: float,
) -> tuple[tuple[InstrumentRepricingCheck, ...], tuple[str, ...]]:
    """Adapt common checks to the baseline's existing issue contract."""
    checks = reprice_calibration_instruments(
        curve=calibration_result.curve,
        quotes=quotes,
        calendar=calendar,
        pass_tolerance_bp=pass_tolerance_bp,
        fail_tolerance_bp=fail_tolerance_bp,
    )
    issues = tuple(
        f"NON_FINITE_REPRICING_ERROR:{check.tenor}"
        for check in checks
        if not isfinite(check.error_bp)
    )
    return checks, issues


def assess_baseline_calibration(
    *,
    calibration_result: GlobalCalibrationResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float | _OmittedTolerance = _OmittedTolerance.OMITTED,
    fail_tolerance_bp: float | _OmittedTolerance = _OmittedTolerance.OMITTED,
) -> BaselineAcceptance:
    """Assess existing calibration; invalid inputs yield rejection issue codes.

    Omit both tolerances to use standard V1 rules. Supplying either tolerance
    explicitly selects custom analysis, even if equal to or stricter than V1;
    the omitted counterpart retains its standard numerical default. Existing
    numeric calls and accepted_for_use/checks keep their analytical meaning.
    Neither path certifies construction history or authorizes publication.
    """
    standard = (
        pass_tolerance_bp is _OmittedTolerance.OMITTED
        and fail_tolerance_bp is _OmittedTolerance.OMITTED
    )
    if pass_tolerance_bp is _OmittedTolerance.OMITTED:
        pass_tolerance_bp = STANDARD_ACCEPTANCE_POLICY.pass_tolerance_bp
    if fail_tolerance_bp is _OmittedTolerance.OMITTED:
        fail_tolerance_bp = STANDARD_ACCEPTANCE_POLICY.fail_tolerance_bp
    _validate_acceptance_tolerances(pass_tolerance_bp, fail_tolerance_bp)
    acceptance_policy = STANDARD_ACCEPTANCE_POLICY if standard else AcceptancePolicy(
        AcceptanceKind.CUSTOM_ANALYTICAL_ASSESSMENT, None,
        pass_tolerance_bp, fail_tolerance_bp,
    )
    quotes = tuple(quotes)
    try:
        prepared = prepare_baseline_inputs(quotes=quotes, calendar=calendar)
        quotes = prepared.quotes
        calendar = prepared.calendar.to_calendar()
        input_issues = ()
    except BaselineInputError as exc:
        prepared = None
        input_issues = exc.issues
    except CalendarCoverageError:
        prepared = None
        input_issues = (
            "CALENDAR_COVERAGE_UNSPECIFIED"
            if calendar.coverage_start is None
            else "CALENDAR_COVERAGE_INSUFFICIENT",
        )
    return _assess_prepared_calibration(
        calibration_result=calibration_result,
        quotes=quotes,
        calendar=calendar,
        prepared=prepared,
        input_issues=input_issues,
        acceptance_policy=acceptance_policy,
    )


def _validate_acceptance_tolerances(pass_bp: float, fail_bp: float) -> None:
    if not isfinite(pass_bp) or not isfinite(fail_bp) or pass_bp < 0 or fail_bp <= pass_bp:
        raise ValueError("Acceptance tolerances must be finite with 0 <= PASS < FAIL.")


def _assess_prepared_calibration(
    *,
    calibration_result: GlobalCalibrationResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    prepared: PreparedBaselineInputs | None,
    input_issues: tuple[str, ...],
    acceptance_policy: AcceptancePolicy,
    financial_context: BaselineFinancialContext | None = None,
) -> BaselineAcceptance:
    """Reuse preflight geometry; repricing still reconstructs instruments independently."""
    pass_tolerance_bp = acceptance_policy.pass_tolerance_bp
    fail_tolerance_bp = acceptance_policy.fail_tolerance_bp
    binding = BaselinePayloadBinding.capture(
        calibration_result, prepared, financial_context, acceptance_policy
    )
    issues = list(input_issues)
    curve = calibration_result.curve
    if calibration_result.interpolation_method != BASELINE_INTERPOLATION_METHOD:
        issues.append("BASELINE_INTERPOLATION_METHOD_MISMATCH")
    if not calibration_result.success:
        issues.append("CALIBRATION_SOLVER_FAILED")

    structural_valid = prepared is not None
    if curve is None:
        issues.append("CURVE_UNAVAILABLE")
        structural_valid = False
    elif not isinstance(curve, CubicContinuousZeroCurve):
        issues.append("BASELINE_CURVE_TYPE_MISMATCH")
        structural_valid = False

    node_dates = getattr(curve, "node_dates", ())
    discount_factors = getattr(curve, "discount_factors", ())
    if len(node_dates) != len(quotes):
        issues.append("NODE_COUNT_MISMATCH")
        structural_valid = False
    if len(discount_factors) != len(quotes):
        issues.append("DISCOUNT_FACTOR_COUNT_MISMATCH")
        structural_valid = False
    if len(node_dates) > 1 and any(
        left >= right for left, right in zip(node_dates, node_dates[1:])
    ):
        issues.append("NODE_DATES_NOT_STRICTLY_INCREASING")
        structural_valid = False
    if any(not isfinite(df) or df <= 0.0 for df in discount_factors):
        issues.append("INVALID_DISCOUNT_FACTORS")
        structural_valid = False
    if len(calibration_result.checks) != len(quotes):
        issues.append("CALIBRATION_CHECK_COUNT_MISMATCH")
        structural_valid = False
    elif tuple(check.tenor for check in calibration_result.checks) != tuple(
        getattr(quote, "tenor", None) for quote in quotes
    ):
        issues.append("CALIBRATION_CHECK_TENOR_MISMATCH")
        structural_valid = False

    if curve is not None and prepared is not None:
        if getattr(curve, "reference_date", None) != prepared.reference_date:
            issues.append("CURVE_REFERENCE_DATE_MISMATCH")
            structural_valid = False
        if tuple(node_dates) != prepared.pillar_dates:
            issues.append("CURVE_PILLAR_DATES_MISMATCH")
            structural_valid = False

    checks = ()
    if structural_valid:
        try:
            checks, repricing_issues = _independently_reprice(
                calibration_result=calibration_result,
                quotes=quotes,
                calendar=calendar,
                pass_tolerance_bp=pass_tolerance_bp,
                fail_tolerance_bp=fail_tolerance_bp,
            )
            issues.extend(repricing_issues)
        except (ValueError, ArithmeticError):
            issues.append("REPRICING_FAILED")

    max_abs_error = max(
        (check.absolute_error_bp for check in checks), default=float("inf")
    )
    if any(not isfinite(check.absolute_error_bp) for check in checks):
        max_abs_error = float("inf")
    if any(check.status != InstrumentValidationStatus.PASS for check in checks):
        issues.append("REPRICING_OUTSIDE_PASS_TOLERANCE")
    accepted_for_use = (
        calibration_result.success
        and structural_valid
        and not issues
        and bool(checks)
    )
    return BaselineAcceptance(
        calibration_success=calibration_result.success,
        accepted_for_use=accepted_for_use,
        structural_valid=structural_valid,
        checks=checks,
        issues=tuple(issues),
        pass_tolerance_bp=pass_tolerance_bp,
        max_abs_repricing_error_bp=max_abs_error,
        fail_tolerance_bp=fail_tolerance_bp,
        binding=binding,
        acceptance_policy=acceptance_policy,
    )


def build_baseline_ftiie_curve(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    initial_discount_factors: Sequence[float] | None = None,
) -> BaselineResult:
    """Validate inputs, then build and assess the selected cubic baseline.

    Invalid quote sets raise BaselineInputError; absent/insufficient calendar
    coverage raises CalendarCoverageError before the solver is invoked.
    """
    if initial_discount_factors is not None:
        initial_discount_factors = tuple(initial_discount_factors)
    policy = BaselineConstructionPolicy(
        baseline_identifier=BASELINE_IDENTIFIER,
        calibration_approach=BASELINE_CALIBRATION_APPROACH,
        interpolation_method=BASELINE_INTERPOLATION_METHOD,
        conventions=replace(FTIIE_OIS_CONVENTIONS),
        acceptance_policy=STANDARD_ACCEPTANCE_POLICY,
    )
    prepared = prepare_baseline_inputs(quotes=quotes, calendar=calendar)
    quotes = prepared.quotes
    calendar = prepared.calendar.to_calendar()
    context = BaselineFinancialContext(prepared, policy)

    calibration_result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=policy.interpolation_method,
            initial_discount_factors=initial_discount_factors,
        )
    )

    acceptance = _assess_prepared_calibration(
        calibration_result=calibration_result,
        quotes=quotes,
        calendar=calendar,
        prepared=prepared,
        input_issues=(),
        acceptance_policy=policy.acceptance_policy,
        financial_context=context,
    )

    return BaselineResult(
        calibration_result=calibration_result,
        acceptance=acceptance,
        financial_context=context,
    )
