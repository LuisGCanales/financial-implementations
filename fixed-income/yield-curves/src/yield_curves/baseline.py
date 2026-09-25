"""Stable policy boundary for the current F-TIIE curve baseline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .bootstrap import OISCalibrationQuote
from .calendars import BusinessCalendar
from .calibration import (
    GlobalCalibrationResult,
    calibrate_ftiie_ois_curve_simultaneously,
)
from .curves import CurveInterpolationMethod
from .instruments import build_ftiie_ois
from .pricing import calculate_par_rate
from .validation import (
    InstrumentRepricingCheck,
    InstrumentValidationStatus,
    classify_repricing_error,
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
) -> tuple[
    tuple[InstrumentRepricingCheck, ...],
    tuple[str, ...],
]:
    checks: list[InstrumentRepricingCheck] = []
    issues: list[str] = []

    for quote in quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=quote.contractual_maturity_date,
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        model_quote = calculate_par_rate(
            ois=ois,
            projection_curve=calibration_result.curve,
            discount_curve=calibration_result.curve,
        )

        error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000.0

        absolute_error_bp = abs(error_bp)
        status = classify_repricing_error(
            absolute_error_bp=absolute_error_bp,
            pass_tolerance_bp=pass_tolerance_bp,
            fail_tolerance_bp=fail_tolerance_bp,
        )

        checks.append(
            InstrumentRepricingCheck(
                tenor=quote.tenor,
                market_quote=quote.par_rate,
                model_quote=model_quote,
                error_bp=error_bp,
                absolute_error_bp=absolute_error_bp,
                status=status,
            )
        )

        if not isfinite(error_bp):
            issues.append(
                f"NON_FINITE_REPRICING_ERROR:{quote.tenor}"
            )

    return tuple(checks), tuple(issues)


def assess_baseline_calibration(
    *,
    calibration_result: GlobalCalibrationResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float = BASELINE_PASS_TOLERANCE_BP,
    fail_tolerance_bp: float = BASELINE_FAIL_TOLERANCE_BP,
) -> BaselineAcceptance:
    """Assess a simultaneous baseline result without using known truth."""

    issues: list[str] = []
    curve = calibration_result.curve

    if (
        calibration_result.interpolation_method
        != BASELINE_INTERPOLATION_METHOD
    ):
        issues.append("BASELINE_INTERPOLATION_METHOD_MISMATCH")

    if not calibration_result.success:
        issues.append("CALIBRATION_SOLVER_FAILED")

    structural_valid = True

    if curve is None:
        issues.append("CURVE_UNAVAILABLE")
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
        left >= right
        for left, right in zip(node_dates, node_dates[1:])
    ):
        issues.append("NODE_DATES_NOT_STRICTLY_INCREASING")
        structural_valid = False

    if any(
        not isfinite(discount_factor)
        or discount_factor <= 0.0
        for discount_factor in discount_factors
    ):
        issues.append("INVALID_DISCOUNT_FACTORS")
        structural_valid = False

    if len(calibration_result.checks) != len(quotes):
        issues.append("CALIBRATION_CHECK_COUNT_MISMATCH")
        structural_valid = False

    if curve is None:
        checks = ()
        repricing_issues = ()
    else:
        checks, repricing_issues = _independently_reprice(
            calibration_result=calibration_result,
            quotes=quotes,
            calendar=calendar,
            pass_tolerance_bp=pass_tolerance_bp,
            fail_tolerance_bp=fail_tolerance_bp,
        )
    issues.extend(repricing_issues)

    max_abs_error = (
        max(
            (check.absolute_error_bp for check in checks),
            default=float("inf"),
        )
    )

    if any(
        check.status != InstrumentValidationStatus.PASS
        for check in checks
    ):
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
    )


def build_baseline_ftiie_curve(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    initial_discount_factors: Sequence[float] | None = None,
) -> BaselineResult:
    """Build and assess the selected simultaneous cubic F-TIIE baseline."""

    calibration_result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=BASELINE_INTERPOLATION_METHOD,
            initial_discount_factors=initial_discount_factors,
        )
    )

    acceptance = assess_baseline_calibration(
        calibration_result=calibration_result,
        quotes=quotes,
        calendar=calendar,
    )

    return BaselineResult(
        calibration_result=calibration_result,
        acceptance=acceptance,
    )