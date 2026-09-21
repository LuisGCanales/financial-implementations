"""Market-tenor parsing and contractual maturity-date utilities.

Tenor resolution is deliberately separated from schedule generation.

Core synthetic-data convention
------------------------------
Project tenors such as 1M, 6M, 1Y, and 30Y are interpreted as
calendar-month / calendar-year offsets from the effective date.

The resulting date is the *unadjusted contractual maturity date*.

Business-day adjustment remains the responsibility of the instrument
schedule layer.

This is a PROJECT DECISION for the synthetic reference framework.
Exact market-tenor interpretation must be revalidated before applying
the engine to a real observed market snapshot.
"""

from __future__ import annotations

import calendar as calendar_module

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class TenorUnit(StrEnum):
    MONTH = "M"
    YEAR = "Y"


@dataclass(frozen=True, slots=True)
class Tenor:
    """Simple month/year market tenor."""

    count: int
    unit: TenorUnit

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError(
                "Tenor count must be positive."
            )

    def __str__(self) -> str:
        return f"{self.count}{self.unit.value}"


def parse_tenor(value: str) -> Tenor:
    """Parse strings such as '1M', '6M', '5Y', or '30Y'."""

    normalized = value.strip().upper()

    if len(normalized) < 2:
        raise ValueError(
            f"Invalid tenor: {value!r}."
        )

    raw_count = normalized[:-1]
    raw_unit = normalized[-1]

    try:
        count = int(raw_count)
    except ValueError as exc:
        raise ValueError(
            f"Invalid tenor count: {value!r}."
        ) from exc

    try:
        unit = TenorUnit(raw_unit)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported tenor unit: {value!r}."
        ) from exc

    return Tenor(
        count=count,
        unit=unit,
    )


def add_calendar_months(
    value: date,
    months: int,
) -> date:
    """Add calendar months, clipping the day when necessary.

    Examples
    --------
    2026-01-31 + 1M -> 2026-02-28

    2024-02-29 + 12M -> 2025-02-28
    """

    if months < 0:
        raise ValueError(
            "Negative month offsets are not supported."
        )

    absolute_month = (
        value.year * 12
        + (value.month - 1)
        + months
    )

    year = absolute_month // 12
    month = absolute_month % 12 + 1

    last_day = calendar_module.monthrange(
        year,
        month,
    )[1]

    day = min(
        value.day,
        last_day,
    )

    return date(
        year,
        month,
        day,
    )


def resolve_contractual_maturity(
    *,
    effective_date: date,
    tenor: Tenor | str,
) -> date:
    """Resolve project tenor into unadjusted contractual maturity.

    No business-day adjustment occurs here.
    """

    if isinstance(tenor, str):
        tenor = parse_tenor(tenor)

    if tenor.unit == TenorUnit.MONTH:
        months = tenor.count

    elif tenor.unit == TenorUnit.YEAR:
        months = tenor.count * 12

    else:
        raise ValueError(
            f"Unsupported tenor unit: {tenor.unit}"
        )

    return add_calendar_months(
        effective_date,
        months,
    )