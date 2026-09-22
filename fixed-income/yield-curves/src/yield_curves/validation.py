"""Validation framework for calibrated F-TIIE curves.

Calibration and validation are intentionally separate.

Calibration asks:
    Can a curve be found that fits the calibration instruments?

Validation asks:
    Should that curve be accepted for downstream use?

Core validation states
----------------------
VALID
    All critical checks pass and all calibration instruments reprice
    within the project PASS tolerance.

REVIEW
    No critical failure exists, but one or more non-critical checks
    require analyst review.

INVALID
    At least one critical validation condition fails.

The framework deliberately performs independent repricing from the
final calibrated curve rather than relying only on calibration-step
residuals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Sequence

from .bootstrap import (
    BootstrapResult,
    OISCalibrationQuote,
)
from .calendars import BusinessCalendar
from .instruments import (
    build_ftiie_ois,
)
from .pricing import (
    calculate_par_rate,
)


class CurveValidationStatus(StrEnum):
    """Overall technical curve-validation state."""

    VALID = "VALID"
    REVIEW = "REVIEW"
    INVALID = "INVALID"


class InstrumentValidationStatus(StrEnum):
    """Validation state for one calibration instrument."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


class ValidationSeverity(StrEnum):
    """Severity attached to a validation issue."""

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation issue requiring visibility."""

    code: str
    severity: ValidationSeverity
    message: str


@dataclass(frozen=True, slots=True)
class InstrumentRepricingCheck:
    """Independent repricing result for one calibration instrument."""

    tenor: str

    market_quote: float
    model_quote: float

    error_bp: float
    absolute_error_bp: float

    status: InstrumentValidationStatus


@dataclass(frozen=True, slots=True)
class CurveValidationReport:
    """Complete validation result for a calibrated curve."""

    status: CurveValidationStatus

    instrument_checks: tuple[
        InstrumentRepricingCheck,
        ...
    ]

    issues: tuple[
        ValidationIssue,
        ...
    ]

    quote_count: int
    node_count: int

    converged_step_count: int

    max_abs_repricing_error_bp: float
    mean_abs_repricing_error_bp: float

    pass_tolerance_bp: float
    fail_tolerance_bp: float

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity
            == ValidationSeverity.WARNING
            for issue in self.issues
        )

    @property
    def critical_issue_count(self) -> int:
        return sum(
            issue.severity
            == ValidationSeverity.CRITICAL
            for issue in self.issues
        )

    @property
    def passed_instrument_count(self) -> int:
        return sum(
            check.status
            == InstrumentValidationStatus.PASS
            for check in self.instrument_checks
        )

    @property
    def review_instrument_count(self) -> int:
        return sum(
            check.status
            == InstrumentValidationStatus.REVIEW
            for check in self.instrument_checks
        )

    @property
    def failed_instrument_count(self) -> int:
        return sum(
            check.status
            == InstrumentValidationStatus.FAIL
            for check in self.instrument_checks
        )


def classify_repricing_error(
    *,
    absolute_error_bp: float,
    pass_tolerance_bp: float,
    fail_tolerance_bp: float,
) -> InstrumentValidationStatus:
    """Classify one calibration-instrument repricing error.

    Project thresholds
    ------------------
    PASS:
        abs(error) <= pass_tolerance_bp

    REVIEW:
        pass_tolerance_bp < abs(error) <= fail_tolerance_bp

    FAIL:
        abs(error) > fail_tolerance_bp
    """

    if not isfinite(
        absolute_error_bp
    ):
        return InstrumentValidationStatus.FAIL

    if pass_tolerance_bp < 0:
        raise ValueError(
            "PASS tolerance cannot be negative."
        )

    if fail_tolerance_bp <= pass_tolerance_bp:
        raise ValueError(
            "FAIL tolerance must exceed PASS tolerance."
        )

    if absolute_error_bp <= pass_tolerance_bp:
        return InstrumentValidationStatus.PASS

    if absolute_error_bp <= fail_tolerance_bp:
        return InstrumentValidationStatus.REVIEW

    return InstrumentValidationStatus.FAIL


def _validate_quote_set(
    quotes: Sequence[OISCalibrationQuote],
) -> list[ValidationIssue]:
    """Validate calibration-quote integrity."""

    issues: list[ValidationIssue] = []

    if not quotes:
        issues.append(
            ValidationIssue(
                code="EMPTY_QUOTE_SET",
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Calibration quote set is empty."
                ),
            )
        )

        return issues

    seen_tenors: set[str] = set()
    seen_maturities = set()

    previous_maturity = None

    trade_dates = {
        quote.trade_date
        for quote in quotes
    }

    if len(trade_dates) != 1:
        issues.append(
            ValidationIssue(
                code="MULTIPLE_TRADE_DATES",
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Calibration instruments do not share "
                    "a single trade date."
                ),
            )
        )

    for quote in quotes:
        if quote.tenor in seen_tenors:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_TENOR",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        f"Duplicate calibration tenor: "
                        f"{quote.tenor}."
                    ),
                )
            )

        seen_tenors.add(
            quote.tenor
        )

        maturity = (
            quote.contractual_maturity_date
        )

        if maturity in seen_maturities:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_MATURITY",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        "Duplicate contractual maturity: "
                        f"{maturity.isoformat()}."
                    ),
                )
            )

        seen_maturities.add(
            maturity
        )

        if (
            previous_maturity is not None
            and maturity <= previous_maturity
        ):
            issues.append(
                ValidationIssue(
                    code="NON_INCREASING_MATURITY",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        "Calibration maturities are not "
                        "strictly increasing."
                    ),
                )
            )

        previous_maturity = maturity

        if not isfinite(
            quote.par_rate
        ):
            issues.append(
                ValidationIssue(
                    code="NON_FINITE_QUOTE",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        f"Quote for {quote.tenor} "
                        "is not finite."
                    ),
                )
            )

    return issues


def _validate_bootstrap_structure(
    *,
    bootstrap_result: BootstrapResult,
    quotes: Sequence[OISCalibrationQuote],
) -> list[ValidationIssue]:
    """Validate structural properties of the bootstrap result."""

    issues: list[ValidationIssue] = []

    curve = bootstrap_result.curve
    steps = bootstrap_result.steps

    if len(steps) != len(quotes):
        issues.append(
            ValidationIssue(
                code="STEP_COUNT_MISMATCH",
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Calibration-step count does not match "
                    "quote count."
                ),
            )
        )

    if len(curve.node_dates) != len(quotes):
        issues.append(
            ValidationIssue(
                code="NODE_COUNT_MISMATCH",
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Calibrated node count does not match "
                    "quote count."
                ),
            )
        )

    unconverged_steps = [
        step.tenor
        for step in steps
        if not step.converged
    ]

    if unconverged_steps:
        issues.append(
            ValidationIssue(
                code="SOLVER_NOT_CONVERGED",
                severity=ValidationSeverity.CRITICAL,
                message=(
                    "Solver did not converge for: "
                    + ", ".join(
                        unconverged_steps
                    )
                    + "."
                ),
            )
        )

    for discount_factor in (
        curve.discount_factors
    ):
        if (
            not isfinite(
                discount_factor
            )
            or discount_factor <= 0
        ):
            issues.append(
                ValidationIssue(
                    code="INVALID_DISCOUNT_FACTOR",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        "Curve contains a non-finite or "
                        "non-positive discount factor."
                    ),
                )
            )

            break

    # Monotonicity is inspected, but deliberately not treated as a
    # universal validity requirement because negative-rate regimes can
    # legitimately produce increasing discount factors.
    previous_df = 1.0

    non_monotonic = False

    for discount_factor in (
        curve.discount_factors
    ):
        if discount_factor > previous_df:
            non_monotonic = True
            break

        previous_df = (
            discount_factor
        )

    if non_monotonic:
        issues.append(
            ValidationIssue(
                code="NON_MONOTONIC_DISCOUNT_FACTORS",
                severity=ValidationSeverity.WARNING,
                message=(
                    "Discount factors are not monotonically "
                    "decreasing. This is not automatically "
                    "invalid but requires financial review."
                ),
            )
        )

    if quotes:
        expected_reference_date = (
            quotes[0].effective_date
            if hasattr(
                quotes[0],
                "effective_date",
            )
            else None
        )

        if (
            expected_reference_date
            is not None
            and curve.reference_date
            != expected_reference_date
        ):
            issues.append(
                ValidationIssue(
                    code="REFERENCE_DATE_MISMATCH",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        "Curve reference date does not match "
                        "calibration effective date."
                    ),
                )
            )

    return issues


def independently_reprice_calibration_instruments(
    *,
    bootstrap_result: BootstrapResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float = 0.01,
    fail_tolerance_bp: float = 0.10,
) -> tuple[
    InstrumentRepricingCheck,
    ...
]:
    """Independently reprice every calibration instrument.

    This function reconstructs each OIS and reprices it using the
    final curve.

    It does not trust the calibration-step model quote stored during
    sequential calibration.
    """

    curve = bootstrap_result.curve

    checks: list[
        InstrumentRepricingCheck
    ] = []

    for quote in quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        model_quote = (
            calculate_par_rate(
                ois=ois,
                projection_curve=curve,
                discount_curve=curve,
            )
        )

        error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000.0

        absolute_error_bp = abs(
            error_bp
        )

        status = (
            classify_repricing_error(
                absolute_error_bp=(
                    absolute_error_bp
                ),
                pass_tolerance_bp=(
                    pass_tolerance_bp
                ),
                fail_tolerance_bp=(
                    fail_tolerance_bp
                ),
            )
        )

        checks.append(
            InstrumentRepricingCheck(
                tenor=quote.tenor,
                market_quote=(
                    quote.par_rate
                ),
                model_quote=model_quote,
                error_bp=error_bp,
                absolute_error_bp=(
                    absolute_error_bp
                ),
                status=status,
            )
        )

    return tuple(
        checks
    )


def validate_bootstrap_result(
    *,
    bootstrap_result: BootstrapResult,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float = 0.01,
    fail_tolerance_bp: float = 0.10,
    additional_issues: Sequence[
        ValidationIssue
    ] = (),
) -> CurveValidationReport:
    """Validate final calibrated curve.

    `additional_issues` provides an extension point for later curve
    diagnostics such as:

        unusual forward behavior
        perturbation instability
        cross-day movement

    without coupling those diagnostics directly to calibration.
    """

    issues = []

    issues.extend(
        _validate_quote_set(
            quotes
        )
    )

    issues.extend(
        _validate_bootstrap_structure(
            bootstrap_result=(
                bootstrap_result
            ),
            quotes=quotes,
        )
    )

    issues.extend(
        additional_issues
    )

    instrument_checks = (
        independently_reprice_calibration_instruments(
            bootstrap_result=(
                bootstrap_result
            ),
            quotes=quotes,
            calendar=calendar,
            pass_tolerance_bp=(
                pass_tolerance_bp
            ),
            fail_tolerance_bp=(
                fail_tolerance_bp
            ),
        )
    )

    for check in instrument_checks:
        if (
            check.status
            == InstrumentValidationStatus.REVIEW
        ):
            issues.append(
                ValidationIssue(
                    code="REPRICING_REVIEW",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"{check.tenor} repricing error "
                        f"is {check.error_bp:.6f} bp."
                    ),
                )
            )

        elif (
            check.status
            == InstrumentValidationStatus.FAIL
        ):
            issues.append(
                ValidationIssue(
                    code="REPRICING_FAIL",
                    severity=ValidationSeverity.CRITICAL,
                    message=(
                        f"{check.tenor} repricing error "
                        f"is {check.error_bp:.6f} bp."
                    ),
                )
            )

    critical_exists = any(
        issue.severity
        == ValidationSeverity.CRITICAL
        for issue in issues
    )

    warning_exists = any(
        issue.severity
        == ValidationSeverity.WARNING
        for issue in issues
    )

    if critical_exists:
        status = (
            CurveValidationStatus.INVALID
        )

    elif warning_exists:
        status = (
            CurveValidationStatus.REVIEW
        )

    else:
        status = (
            CurveValidationStatus.VALID
        )

    absolute_errors = [
        check.absolute_error_bp
        for check in instrument_checks
    ]

    if absolute_errors:
        max_abs_error = max(
            absolute_errors
        )

        mean_abs_error = (
            sum(
                absolute_errors
            )
            / len(
                absolute_errors
            )
        )

    else:
        max_abs_error = float("nan")
        mean_abs_error = float("nan")

    converged_step_count = sum(
        step.converged
        for step in bootstrap_result.steps
    )

    return CurveValidationReport(
        status=status,
        instrument_checks=instrument_checks,
        issues=tuple(
            issues
        ),
        quote_count=len(
            quotes
        ),
        node_count=len(
            bootstrap_result
            .curve
            .node_dates
        ),
        converged_step_count=(
            converged_step_count
        ),
        max_abs_repricing_error_bp=(
            max_abs_error
        ),
        mean_abs_repricing_error_bp=(
            mean_abs_error
        ),
        pass_tolerance_bp=(
            pass_tolerance_bp
        ),
        fail_tolerance_bp=(
            fail_tolerance_bp
        ),
    )