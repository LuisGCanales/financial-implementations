"""Overnight observation and compounding mechanics for F-TIIE OIS.

An F-TIIE OIS coupon is not represented by one fixing.

Instead, each coupon period contains a sequence of overnight
observations. A fixing applies from its business-day accrual start
until the next applicable business day, potentially spanning
weekends or holidays.

Example
-------

Friday fixing
    ↓
Friday → Monday
    ↓
3 calendar days of accrual
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Mapping, Sequence

from .calendars import BusinessCalendar
from .conventions import (
    FTIIE_OIS_CONVENTIONS,
    FTiieOISConventions,
)


@dataclass(frozen=True, slots=True)
class OvernightObservation:
    """One overnight-rate observation inside an OIS coupon period."""

    observation_number: int

    fixing_date: date

    accrual_start_date: date
    accrual_end_date: date

    calendar_days: int
    accrual_factor: float


@dataclass(frozen=True, slots=True)
class OvernightCompoundingResult:
    """Result of compounding realized overnight observations."""

    period_start_date: date
    period_end_date: date

    calendar_days: int
    period_accrual_factor: float

    growth_factor: float
    compounded_return: float
    annualized_rate: float

    observation_count: int


def generate_overnight_observations(
    *,
    period_start_date: date,
    period_end_date: date,
    calendar: BusinessCalendar,
    conventions: FTiieOISConventions = FTIIE_OIS_CONVENTIONS,
) -> tuple[OvernightObservation, ...]:
    """Generate overnight observations for one F-TIIE OIS coupon.

    Each observation starts on an MXMC business day.

    Its fixing applies until the next MXMC business day, or until
    the coupon-period end if that occurs first.

    The number of calendar days between those dates determines the
    ACT/360 weight of that fixing.

    Parameters
    ----------
    period_start_date
        Adjusted coupon-period start.

    period_end_date
        Adjusted coupon-period end.

    calendar
        Calendar used to identify valid fixing days.

    conventions
        Canonical F-TIIE OIS conventions.

    Returns
    -------
    tuple[OvernightObservation, ...]
        Ordered fixing/accrual observations.
    """

    if period_end_date <= period_start_date:
        raise ValueError(
            "Period end date must be after period start date."
        )

    if not calendar.is_business_day(period_start_date):
        raise ValueError(
            "Period start date must be a business day."
        )

    if not calendar.is_business_day(period_end_date):
        raise ValueError(
            "Period end date must be a business day."
        )

    if conventions.fixing_day_type.value != "BUSINESS":
        raise NotImplementedError(
            "Core v1 currently supports business-day fixings only."
        )

    observations: list[OvernightObservation] = []

    accrual_start = period_start_date
    observation_number = 1

    while accrual_start < period_end_date:
        next_business_day = calendar.add_business_days(
            accrual_start,
            1,
        )

        accrual_end = min(
            next_business_day,
            period_end_date,
        )

        fixing_base_date = calendar.add_business_days(
            accrual_start,
            -conventions.fixing_offset_business_days,
        )

        fixing_date = calendar.adjust(
            fixing_base_date,
            conventions.fixing_adjustment,
        )

        calendar_days = (
            accrual_end - accrual_start
        ).days

        if calendar_days <= 0:
            raise ValueError(
                "Observation accrual interval must be positive."
            )

        accrual_factor = calendar_days / 360.0

        observations.append(
            OvernightObservation(
                observation_number=observation_number,
                fixing_date=fixing_date,
                accrual_start_date=accrual_start,
                accrual_end_date=accrual_end,
                calendar_days=calendar_days,
                accrual_factor=accrual_factor,
            )
        )

        accrual_start = accrual_end
        observation_number += 1

    total_observation_days = sum(
        observation.calendar_days
        for observation in observations
    )

    actual_period_days = (
        period_end_date - period_start_date
    ).days

    if total_observation_days != actual_period_days:
        raise RuntimeError(
            "Overnight observations do not cover the full "
            "coupon period."
        )

    return tuple(observations)


def compound_overnight_fixings(
    *,
    observations: Sequence[OvernightObservation],
    fixings: Mapping[date, float],
) -> OvernightCompoundingResult:
    """Compound realized overnight F-TIIE fixings.

    Rates must be supplied as decimal annualized rates.

    Example
    -------
    7.25% -> 0.0725

    For each observation:

        factor_i = 1 + r_i * d_i / 360

    and:

        growth_factor = product(factor_i)

    The compounded coupon return is:

        growth_factor - 1

    The annualized compounded rate is:

        compounded_return / period_ACT_360
    """

    if not observations:
        raise ValueError(
            "At least one overnight observation is required."
        )

    growth_factor = 1.0

    for observation in observations:
        try:
            rate = fixings[observation.fixing_date]
        except KeyError as exc:
            raise KeyError(
                "Missing fixing for "
                f"{observation.fixing_date.isoformat()}."
            ) from exc

        if not isfinite(rate):
            raise ValueError(
                "Fixing rate must be finite."
            )

        daily_growth_factor = (
            1.0
            + rate * observation.accrual_factor
        )

        if daily_growth_factor <= 0:
            raise ValueError(
                "Fixing implies a non-positive "
                "accrual growth factor."
            )

        growth_factor *= daily_growth_factor

    first = observations[0]
    last = observations[-1]

    period_start = first.accrual_start_date
    period_end = last.accrual_end_date

    calendar_days = (
        period_end - period_start
    ).days

    period_accrual_factor = (
        calendar_days / 360.0
    )

    compounded_return = (
        growth_factor - 1.0
    )

    annualized_rate = (
        compounded_return
        / period_accrual_factor
    )

    return OvernightCompoundingResult(
        period_start_date=period_start,
        period_end_date=period_end,
        calendar_days=calendar_days,
        period_accrual_factor=period_accrual_factor,
        growth_factor=growth_factor,
        compounded_return=compounded_return,
        annualized_rate=annualized_rate,
        observation_count=len(observations),
    )
