"""Shared instrument repricing, independent of calibration result containers.

The final curve is used for both projection and discounting, matching the
current same-curve assumption. Callers decide curve-level acceptance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Sequence

from .calendars import BusinessCalendar
from .curves import DiscountFactorCurve
from .instruments import build_ftiie_ois
from .pricing import calculate_par_rate
from .quotes import OISCalibrationQuote


class InstrumentValidationStatus(StrEnum):
    """Validation state for one calibration instrument."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"



@dataclass(frozen=True, slots=True)
class InstrumentRepricingCheck:
    """Independent repricing result for one calibration instrument."""

    tenor: str

    market_quote: float
    model_quote: float

    error_bp: float
    absolute_error_bp: float

    status: InstrumentValidationStatus



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



def reprice_calibration_instruments(
    *,
    curve: DiscountFactorCurve,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    pass_tolerance_bp: float = 0.01,
    fail_tolerance_bp: float = 0.10,
) -> tuple[InstrumentRepricingCheck, ...]:
    """Rebuild each OIS and calculate its par rate from the final curve.

    Stored solver residuals are not inputs to this calculation. Non-finite
    errors retain their numerical values and are classified as FAIL.
    """
    checks: list[InstrumentRepricingCheck] = []
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
            projection_curve=curve,
            discount_curve=curve,
        )
        error_bp = (model_quote - quote.par_rate) * 10_000.0
        absolute_error_bp = abs(error_bp)
        status = classify_repricing_error(
            absolute_error_bp=absolute_error_bp,
            pass_tolerance_bp=pass_tolerance_bp,
            fail_tolerance_bp=fail_tolerance_bp,
        )
        checks.append(InstrumentRepricingCheck(
            tenor=quote.tenor,
            market_quote=quote.par_rate,
            model_quote=model_quote,
            error_bp=error_bp,
            absolute_error_bp=absolute_error_bp,
            status=status,
        ))
    return tuple(checks)
