"""Stable policy boundary for the current F-TIIE curve baseline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .quotes import OISCalibrationQuote
from .calendars import BusinessCalendar, CalendarCoverageError
from .calibration import (
    GlobalCalibrationResult,
    calibrate_ftiie_ois_curve_simultaneously,
)
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


@dataclass(frozen=True, slots=True)
class BaselineAcceptance:
    """Operational acceptance result for one baseline calibration."""

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


@dataclass(frozen=True, slots=True)
class BaselineResult:
    """Calibration result plus the explicit operational acceptance result.

    The calibration result remains the single source of truth for the curve,
    solver diagnostics, and calibration checks. This wrapper only separates
    those facts from the policy decision about downstream use.
    """

    calibration_result: GlobalCalibrationResult
    acceptance: BaselineAcceptance

    @property
    def curve(self):
        """Return the calibrated baseline curve."""

        return self.calibration_result.curve

    @property
    def accepted_for_use(self) -> bool:
        """Return whether the result passed operational acceptance."""

        return self.acceptance.accepted_for_use


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
    pass_tolerance_bp: float = BASELINE_PASS_TOLERANCE_BP,
    fail_tolerance_bp: float = BASELINE_FAIL_TOLERANCE_BP,
) -> BaselineAcceptance:
    """Assess existing calibration; invalid inputs yield rejection issue codes."""
    _validate_acceptance_tolerances(pass_tolerance_bp, fail_tolerance_bp)
    quotes = tuple(quotes)
    try:
        prepared = prepare_baseline_inputs(quotes=quotes, calendar=calendar)
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
        pass_tolerance_bp=pass_tolerance_bp,
        fail_tolerance_bp=fail_tolerance_bp,
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
    pass_tolerance_bp: float,
    fail_tolerance_bp: float,
) -> BaselineAcceptance:
    """Reuse preflight geometry; repricing still reconstructs instruments independently."""
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
    prepared = prepare_baseline_inputs(quotes=quotes, calendar=calendar)
    quotes = prepared.quotes

    calibration_result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=BASELINE_INTERPOLATION_METHOD,
            initial_discount_factors=initial_discount_factors,
        )
    )

    acceptance = _assess_prepared_calibration(
        calibration_result=calibration_result,
        quotes=quotes,
        calendar=calendar,
        prepared=prepared,
        input_issues=(),
        pass_tolerance_bp=BASELINE_PASS_TOLERANCE_BP,
        fail_tolerance_bp=BASELINE_FAIL_TOLERANCE_BP,
    )

    return BaselineResult(
        calibration_result=calibration_result,
        acceptance=acceptance,
    )