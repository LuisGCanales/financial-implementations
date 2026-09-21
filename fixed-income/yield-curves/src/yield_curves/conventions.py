"""Financial conventions for the MXN F-TIIE OIS implementation.

This module contains financial definitions only.

It should not contain:
- market data;
- curve calibration;
- schedule-generation algorithms;
- pricing logic.

The objective is to make material financial conventions explicit and
independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class BusinessDayConvention(StrEnum):
    """Supported business-day adjustment conventions."""

    NONE = "NONE"
    FOLLOWING = "FOLLOWING"
    PRECEDING = "PRECEDING"


class DayCountConvention(StrEnum):
    """Supported accrual conventions."""

    ACT_360 = "ACT_360"


class RollConvention(StrEnum):
    """Schedule roll convention."""

    NONE = "NONE"


class DateRelativeTo(StrEnum):
    """Reference point used by contractual date rules."""

    END_PERIOD = "END_PERIOD"


class DayType(StrEnum):
    """Type of day used for date offsets."""

    BUSINESS = "BUSINESS"
    CALENDAR = "CALENDAR"


class CompoundingMethod(StrEnum):
    """Floating-leg compounding method."""

    ISDA_STANDARD = "ISDA_STANDARD"


class SpreadTreatment(StrEnum):
    """Treatment of contractual spread during compounding."""

    SPREAD_EXCLUSIVE = "SPREAD_EXCLUSIVE"


@dataclass(frozen=True, slots=True)
class FTiieOISConventions:
    """Canonical Core-v1 convention profile for MXN F-TIIE OIS.

    Values in this object correspond to the financial specification.
    They should not be changed locally inside pricing or schedule code.
    """

    currency: str = "MXN"
    benchmark: str = "FTIIE"
    floating_index: str = "MXN_TIIE_ON_OIS_COMPOUND"

    calendar_id: str = "MXMC"

    effective_date_lag_business_days: int = 2

    day_count: DayCountConvention = DayCountConvention.ACT_360

    payment_frequency_days: int = 28
    calculation_frequency_days: int = 28
    reset_frequency_days: int = 28

    roll_convention: RollConvention = RollConvention.NONE

    start_date_adjustment: BusinessDayConvention = (
        BusinessDayConvention.FOLLOWING
    )
    maturity_date_adjustment: BusinessDayConvention = (
        BusinessDayConvention.FOLLOWING
    )
    calculation_period_adjustment: BusinessDayConvention = (
        BusinessDayConvention.FOLLOWING
    )

    payment_relative_to: DateRelativeTo = DateRelativeTo.END_PERIOD
    payment_adjustment: BusinessDayConvention = (
        BusinessDayConvention.FOLLOWING
    )
    payment_lag_business_days: int = 2

    reset_relative_to: DateRelativeTo = DateRelativeTo.END_PERIOD
    reset_adjustment: BusinessDayConvention = (
        BusinessDayConvention.FOLLOWING
    )

    floating_index_tenor_days: int = 1

    fixing_offset_business_days: int = 0
    fixing_day_type: DayType = DayType.BUSINESS
    fixing_adjustment: BusinessDayConvention = (
        BusinessDayConvention.PRECEDING
    )

    compounding_method: CompoundingMethod = (
        CompoundingMethod.ISDA_STANDARD
    )
    spread_treatment: SpreadTreatment = SpreadTreatment.SPREAD_EXCLUSIVE

    floating_spread: float = 0.0
    calibration_notional: float = 1.0

    def __post_init__(self) -> None:
        if self.effective_date_lag_business_days < 0:
            raise ValueError(
                "Effective-date lag cannot be negative."
            )

        if self.payment_frequency_days <= 0:
            raise ValueError(
                "Payment frequency must be positive."
            )

        if self.calculation_frequency_days <= 0:
            raise ValueError(
                "Calculation frequency must be positive."
            )

        if self.reset_frequency_days <= 0:
            raise ValueError(
                "Reset frequency must be positive."
            )

        if self.payment_lag_business_days < 0:
            raise ValueError(
                "Payment lag cannot be negative."
            )

        if self.floating_index_tenor_days <= 0:
            raise ValueError(
                "Floating-index tenor must be positive."
            )

        if self.calibration_notional <= 0:
            raise ValueError(
                "Calibration notional must be positive."
            )


FTIIE_OIS_CONVENTIONS = FTiieOISConventions()


def act_360(start_date: date, end_date: date) -> float:
    """Return ACT/360 year fraction between two dates.

    Parameters
    ----------
    start_date
        Accrual-period start date.
    end_date
        Accrual-period end date.

    Returns
    -------
    float
        Actual number of calendar days divided by 360.

    Raises
    ------
    ValueError
        If end_date precedes start_date.
    """

    if end_date < start_date:
        raise ValueError(
            "End date cannot precede start date."
        )

    actual_days = (end_date - start_date).days

    return actual_days / 360.0