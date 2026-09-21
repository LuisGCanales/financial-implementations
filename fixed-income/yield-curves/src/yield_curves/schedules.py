"""Schedule construction for MXN F-TIIE OIS instruments.

This module handles contractual period boundaries, business-day
adjustments, payment dates, and accrual factors.

It does not yet construct the daily overnight fixing observation
schedule. That will be implemented separately because an OIS coupon
contains multiple overnight observations rather than one fixing per
coupon period.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .calendars import BusinessCalendar
from .conventions import (
    FTIIE_OIS_CONVENTIONS,
    FTiieOISConventions,
    act_360,
)


@dataclass(frozen=True, slots=True)
class OISPeriod:
    """One calculation/payment period of an OIS."""

    period_number: int

    unadjusted_start_date: date
    unadjusted_end_date: date

    start_date: date
    end_date: date

    payment_date: date

    accrual_factor: float


@dataclass(frozen=True, slots=True)
class OISSchedule:
    """Complete coupon schedule for a spot-starting OIS."""

    effective_date: date
    contractual_maturity_date: date
    adjusted_maturity_date: date

    periods: tuple[OISPeriod, ...]

    @property
    def number_of_periods(self) -> int:
        return len(self.periods)


def calculate_effective_date(
    trade_date: date,
    calendar: BusinessCalendar,
    conventions: FTiieOISConventions = FTIIE_OIS_CONVENTIONS,
) -> date:
    """Calculate the canonical T+2 effective date.

    The trade date is expected to be a valid business day.
    We fail explicitly rather than silently adjusting an invalid
    trade date.
    """

    if not calendar.is_business_day(trade_date):
        raise ValueError(
            "Trade date must be an MXMC business day."
        )

    effective_date = calendar.add_business_days(
        trade_date,
        conventions.effective_date_lag_business_days,
    )

    return calendar.adjust(
        effective_date,
        conventions.start_date_adjustment,
    )


def _build_unadjusted_boundaries(
    effective_date: date,
    maturity_date: date,
    *,
    frequency_days: int,
) -> tuple[date, ...]:
    """Construct deterministic calendar-day period boundaries.

    Full periods use exact calendar-day frequency.

    If contractual maturity is not an exact multiple of the
    frequency from effective date, the final period is a stub.

    No business-day adjustment occurs here.
    """

    if maturity_date <= effective_date:
        raise ValueError(
            "Maturity date must be after effective date."
        )

    if frequency_days <= 0:
        raise ValueError(
            "Frequency must be positive."
        )

    boundaries = [effective_date]

    next_boundary = effective_date + timedelta(
        days=frequency_days
    )

    while next_boundary < maturity_date:
        boundaries.append(next_boundary)

        next_boundary += timedelta(
            days=frequency_days
        )

    boundaries.append(maturity_date)

    return tuple(boundaries)


def generate_ois_schedule(
    *,
    effective_date: date,
    maturity_date: date,
    calendar: BusinessCalendar,
    conventions: FTiieOISConventions = FTIIE_OIS_CONVENTIONS,
) -> OISSchedule:
    """Generate Core-v1 MXN F-TIIE OIS coupon schedule.

    Parameters
    ----------
    effective_date
        Contractual effective date.
    maturity_date
        Contractual, unadjusted maturity date.

        This is intentionally explicit. Mapping quote labels such as
        "1Y" or "5Y" into contractual maturity dates is a separate
        market-convention problem and is not silently assumed here.

    calendar
        Business calendar used for adjustments.

    conventions
        Frozen instrument convention profile.
    """

    boundaries = _build_unadjusted_boundaries(
        effective_date=effective_date,
        maturity_date=maturity_date,
        frequency_days=conventions.calculation_frequency_days,
    )

    adjusted_boundaries: list[date] = []

    for index, boundary in enumerate(boundaries):
        if index == 0:
            convention = conventions.start_date_adjustment

        elif index == len(boundaries) - 1:
            convention = conventions.maturity_date_adjustment

        else:
            convention = (
                conventions.calculation_period_adjustment
            )

        adjusted_boundaries.append(
            calendar.adjust(
                boundary,
                convention,
            )
        )

    for earlier, later in zip(
        adjusted_boundaries,
        adjusted_boundaries[1:],
    ):
        if later <= earlier:
            raise ValueError(
                "Business-day adjustment produced a "
                "non-increasing schedule."
            )

    periods: list[OISPeriod] = []

    for period_index in range(
        len(adjusted_boundaries) - 1
    ):
        unadjusted_start = boundaries[period_index]
        unadjusted_end = boundaries[period_index + 1]

        start = adjusted_boundaries[period_index]
        end = adjusted_boundaries[period_index + 1]

        payment_date = calendar.add_business_days(
            end,
            conventions.payment_lag_business_days,
        )

        payment_date = calendar.adjust(
            payment_date,
            conventions.payment_adjustment,
        )

        accrual_factor = act_360(
            start,
            end,
        )

        periods.append(
            OISPeriod(
                period_number=period_index + 1,
                unadjusted_start_date=unadjusted_start,
                unadjusted_end_date=unadjusted_end,
                start_date=start,
                end_date=end,
                payment_date=payment_date,
                accrual_factor=accrual_factor,
            )
        )

    return OISSchedule(
        effective_date=adjusted_boundaries[0],
        contractual_maturity_date=maturity_date,
        adjusted_maturity_date=adjusted_boundaries[-1],
        periods=tuple(periods),
    )