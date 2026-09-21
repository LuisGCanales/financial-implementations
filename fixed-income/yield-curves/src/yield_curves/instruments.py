"""Financial-instrument representations used by the curve engine.

This module combines contractual schedules and overnight observation
schedules into explicit financial instruments.

It deliberately does not perform:

- curve calibration;
- discounting;
- projected-rate generation;
- present-value calculations.

Those responsibilities belong to later layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite

from .calendars import BusinessCalendar
from .conventions import (
    FTIIE_OIS_CONVENTIONS,
    FTiieOISConventions,
)
from .observations import (
    OvernightObservation,
    generate_overnight_observations,
)
from .schedules import (
    calculate_effective_date,
    generate_ois_schedule,
)


@dataclass(frozen=True, slots=True)
class FixedLegCoupon:
    """One fixed-leg coupon of an F-TIIE OIS."""

    period_number: int

    accrual_start_date: date
    accrual_end_date: date
    payment_date: date

    accrual_factor: float

    notional: float
    fixed_rate: float

    @property
    def amount(self) -> float:
        """Return the undiscounted contractual fixed coupon amount."""

        return (
            self.notional
            * self.fixed_rate
            * self.accrual_factor
        )


@dataclass(frozen=True, slots=True)
class FloatingLegCoupon:
    """One floating-leg coupon of an F-TIIE OIS.

    The coupon contains the overnight observation structure required
    to compound F-TIIE across the calculation period.

    No floating coupon amount is calculated here because the rate may
    be:

    - fully realized from historical fixings;
    - partially realized;
    - fully projected from a curve.
    """

    period_number: int

    accrual_start_date: date
    accrual_end_date: date
    payment_date: date

    accrual_factor: float

    notional: float
    spread: float

    observations: tuple[OvernightObservation, ...]


@dataclass(frozen=True, slots=True)
class FTiieOIS:
    """Canonical Core-v1 MXN F-TIIE Overnight Index Swap.

    The object represents contractual instrument mechanics only.

    Pricing context, market data, projection curves, and discount
    curves are intentionally external.
    """

    trade_date: date

    effective_date: date

    contractual_maturity_date: date
    adjusted_maturity_date: date

    fixed_rate: float
    notional: float
    floating_spread: float

    calendar_id: str

    fixed_leg: tuple[FixedLegCoupon, ...]
    floating_leg: tuple[FloatingLegCoupon, ...]

    conventions: FTiieOISConventions

    def __post_init__(self) -> None:
        if not isfinite(self.fixed_rate):
            raise ValueError(
                "Fixed rate must be finite."
            )

        if not isfinite(self.floating_spread):
            raise ValueError(
                "Floating spread must be finite."
            )

        if not isfinite(self.notional):
            raise ValueError(
                "Notional must be finite."
            )

        if self.notional <= 0:
            raise ValueError(
                "Notional must be positive."
            )

        if self.effective_date >= self.adjusted_maturity_date:
            raise ValueError(
                "Adjusted maturity date must follow "
                "effective date."
            )

        if not self.fixed_leg:
            raise ValueError(
                "OIS must contain at least one coupon period."
            )

        if len(self.fixed_leg) != len(self.floating_leg):
            raise ValueError(
                "Fixed and floating legs must contain "
                "the same number of coupon periods."
            )

        for fixed_coupon, floating_coupon in zip(
            self.fixed_leg,
            self.floating_leg,
        ):
            if (
                fixed_coupon.period_number
                != floating_coupon.period_number
            ):
                raise ValueError(
                    "Fixed and floating coupon periods "
                    "are not aligned."
                )

            if (
                fixed_coupon.accrual_start_date
                != floating_coupon.accrual_start_date
            ):
                raise ValueError(
                    "Fixed and floating accrual starts "
                    "are not aligned."
                )

            if (
                fixed_coupon.accrual_end_date
                != floating_coupon.accrual_end_date
            ):
                raise ValueError(
                    "Fixed and floating accrual ends "
                    "are not aligned."
                )

            if (
                fixed_coupon.payment_date
                != floating_coupon.payment_date
            ):
                raise ValueError(
                    "Fixed and floating payment dates "
                    "are not aligned."
                )

    @property
    def number_of_periods(self) -> int:
        """Return number of contractual coupon periods."""

        return len(self.fixed_leg)

    @property
    def final_payment_date(self) -> date:
        """Return latest contractual payment date."""

        return self.fixed_leg[-1].payment_date


    @property
    def last_relevant_date(self) -> date:
        """Return latest date currently required for OIS valuation."""

        return max(
            self.adjusted_maturity_date,
            self.final_payment_date,
        )


def build_ftiie_ois(
    *,
    trade_date: date,
    maturity_date: date,
    fixed_rate: float,
    calendar: BusinessCalendar,
    notional: float = 1.0,
    floating_spread: float = 0.0,
    conventions: FTiieOISConventions = FTIIE_OIS_CONVENTIONS,
) -> FTiieOIS:
    """Build a canonical spot-starting F-TIIE OIS.

    Parameters
    ----------
    trade_date
        Contract trade date.

    maturity_date
        Explicit contractual, unadjusted maturity date.

        Market-tenor labels such as ``1Y`` or ``5Y`` are intentionally
        not resolved here. Tenor-to-maturity conversion will be handled
        by a separate market-instrument construction layer.

    fixed_rate
        Contractual fixed rate expressed as a decimal.

        Example:
            7.25% -> 0.0725

    calendar
        Business calendar used for contractual date generation.

    notional
        Positive MXN notional.

    floating_spread
        Floating-leg spread expressed as a decimal.

        Canonical calibration instruments use zero spread.

    conventions
        Explicit F-TIIE OIS financial convention profile.
    """

    if not isfinite(fixed_rate):
        raise ValueError(
            "Fixed rate must be finite."
        )

    if not isfinite(notional):
        raise ValueError(
            "Notional must be finite."
        )

    if notional <= 0:
        raise ValueError(
            "Notional must be positive."
        )

    if not isfinite(floating_spread):
        raise ValueError(
            "Floating spread must be finite."
        )

    effective_date = calculate_effective_date(
        trade_date=trade_date,
        calendar=calendar,
        conventions=conventions,
    )

    schedule = generate_ois_schedule(
        effective_date=effective_date,
        maturity_date=maturity_date,
        calendar=calendar,
        conventions=conventions,
    )

    fixed_leg: list[FixedLegCoupon] = []
    floating_leg: list[FloatingLegCoupon] = []

    for period in schedule.periods:
        fixed_coupon = FixedLegCoupon(
            period_number=period.period_number,
            accrual_start_date=period.start_date,
            accrual_end_date=period.end_date,
            payment_date=period.payment_date,
            accrual_factor=period.accrual_factor,
            notional=notional,
            fixed_rate=fixed_rate,
        )

        observations = generate_overnight_observations(
            period_start_date=period.start_date,
            period_end_date=period.end_date,
            calendar=calendar,
            conventions=conventions,
        )

        floating_coupon = FloatingLegCoupon(
            period_number=period.period_number,
            accrual_start_date=period.start_date,
            accrual_end_date=period.end_date,
            payment_date=period.payment_date,
            accrual_factor=period.accrual_factor,
            notional=notional,
            spread=floating_spread,
            observations=observations,
        )

        fixed_leg.append(fixed_coupon)
        floating_leg.append(floating_coupon)

    return FTiieOIS(
        trade_date=trade_date,
        effective_date=schedule.effective_date,
        contractual_maturity_date=(
            schedule.contractual_maturity_date
        ),
        adjusted_maturity_date=(
            schedule.adjusted_maturity_date
        ),
        fixed_rate=fixed_rate,
        notional=notional,
        floating_spread=floating_spread,
        calendar_id=calendar.name,
        fixed_leg=tuple(fixed_leg),
        floating_leg=tuple(floating_leg),
        conventions=conventions,
    )