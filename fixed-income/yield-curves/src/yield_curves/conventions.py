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

from dataclasses import dataclass, fields
from datetime import date
from enum import StrEnum
from math import isfinite


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
        validate_core_v1_conventions(self)


def validate_core_v1_conventions(conventions: FTiieOISConventions) -> None:
    """Require the closed Core-v1 profile before using financial primitives.

    Dataclass defaults are the single authority for supported values. Fields
    without a runtime selector are validated fixed descriptors, not extension
    points. Calendar identity denotes a family, not the supplied instance name.
    Calibration notional does not constrain a downstream instrument's notional.
    """

    if not isinstance(conventions, FTiieOISConventions):
        raise ValueError("Core-v1 requires FTiieOISConventions.")

    for field in fields(FTiieOISConventions):
        expected = field.default
        actual = getattr(conventions, field.name)
        # Preserve enums and integral day counts; allow numeric 0/1 for
        # spread/notional without requiring a float literal.
        valid_type = (
            type(actual) in (int, float)
            if type(expected) is float
            else type(actual) is type(expected)
        )
        if not valid_type or actual != expected:
            raise ValueError(
                f"Core-v1 requires {field.name}={expected!r}; got {actual!r}."
            )


def validate_zero_floating_spread(spread: float) -> None:
    """Reject unsupported contractual spreads before construction or pricing."""

    if not isfinite(spread):
        raise ValueError("Floating spread must be finite.")
    if spread != 0.0:
        raise NotImplementedError("Core-v1 supports zero floating spread only.")


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