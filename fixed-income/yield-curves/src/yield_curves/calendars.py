"""Business-calendar utilities used by financial instruments.

The canonical MXMC holiday set is treated as data and injected into the
calendar. It is deliberately not hardcoded in this module.

This keeps separate:

    calendar logic
    vs.
    calendar data
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from .conventions import BusinessDayConvention


WEEKEND_DAYS = frozenset({5, 6})
# Python weekday:
# Monday = 0
# ...
# Saturday = 5
# Sunday = 6


@dataclass(frozen=True, slots=True)
class BusinessCalendar:
    """Simple deterministic business calendar.

    Parameters
    ----------
    name
        Calendar identifier.
    holidays
        Explicit non-weekend holidays.
    weekend_days
        Weekday numbers considered weekends.
    """

    name: str
    holidays: frozenset[date] = field(default_factory=frozenset)
    weekend_days: frozenset[int] = WEEKEND_DAYS

    @classmethod
    def from_holidays(
        cls,
        name: str,
        holidays: Iterable[date],
    ) -> "BusinessCalendar":
        """Construct a calendar from an iterable of holiday dates."""

        return cls(
            name=name,
            holidays=frozenset(holidays),
        )

    def is_weekend(self, value: date) -> bool:
        """Return True when date falls on configured weekend."""

        return value.weekday() in self.weekend_days

    def is_holiday(self, value: date) -> bool:
        """Return True when date appears in explicit holiday set."""

        return value in self.holidays

    def is_business_day(self, value: date) -> bool:
        """Return True when date is neither weekend nor holiday."""

        return (
            not self.is_weekend(value)
            and not self.is_holiday(value)
        )

    def following(self, value: date) -> date:
        """Return first business day on or after value."""

        adjusted = value

        while not self.is_business_day(adjusted):
            adjusted += timedelta(days=1)

        return adjusted

    def preceding(self, value: date) -> date:
        """Return first business day on or before value."""

        adjusted = value

        while not self.is_business_day(adjusted):
            adjusted -= timedelta(days=1)

        return adjusted

    def adjust(
        self,
        value: date,
        convention: BusinessDayConvention,
    ) -> date:
        """Adjust a date under the requested convention."""

        if convention == BusinessDayConvention.NONE:
            return value

        if convention == BusinessDayConvention.FOLLOWING:
            return self.following(value)

        if convention == BusinessDayConvention.PRECEDING:
            return self.preceding(value)

        raise ValueError(
            f"Unsupported business-day convention: {convention}"
        )

    def add_business_days(
        self,
        value: date,
        offset: int,
    ) -> date:
        """Shift a date by an exact number of business days.

        The starting date is not counted.

        Examples
        --------
        Friday + 1 business day -> Monday
        Monday - 1 business day -> Friday

        An offset of zero returns the original date unchanged.
        Business-day adjustment, if needed, should be performed
        separately and explicitly.
        """

        if offset == 0:
            return value

        direction = 1 if offset > 0 else -1
        remaining = abs(offset)

        current = value

        while remaining:
            current += timedelta(days=direction)

            if self.is_business_day(current):
                remaining -= 1

        return current


def load_holidays_csv(
    path: str | Path,
    *,
    date_column: str = "date",
) -> frozenset[date]:
    """Load ISO-formatted holiday dates from a CSV file.

    Expected format
    ---------------
    date
    2026-01-01
    2026-02-02

    No assumptions are made about the source or correctness of
    the holiday file. Provenance belongs in the data documentation.
    """

    path = Path(path)

    holidays: set[date] = set()

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if date_column not in (reader.fieldnames or []):
            raise ValueError(
                f"CSV must contain column '{date_column}'."
            )

        for row in reader:
            raw_value = row[date_column].strip()

            if not raw_value:
                continue

            holidays.add(
                date.fromisoformat(raw_value)
            )

    return frozenset(holidays)


def build_mxmc_calendar(
    holidays: Iterable[date],
) -> BusinessCalendar:
    """Construct the project MXMC calendar from verified holiday data."""

    return BusinessCalendar.from_holidays(
        name="MXMC",
        holidays=holidays,
    )
    
    
def build_mxmc_calendar_from_csv(
    path: str | Path,
) -> BusinessCalendar:
    """Build the project MXMC calendar from a frozen holiday dataset."""

    holidays = load_holidays_csv(path)

    return build_mxmc_calendar(holidays)


def _nth_weekday_of_month(
    *,
    year: int,
    month: int,
    weekday: int,
    occurrence: int,
) -> date:
    """Return nth occurrence of weekday in a calendar month.

    Monday = 0
    ...
    Sunday = 6
    """

    if occurrence <= 0:
        raise ValueError(
            "Occurrence must be positive."
        )

    first = date(
        year,
        month,
        1,
    )

    days_until_weekday = (
        weekday - first.weekday()
    ) % 7

    result = (
        first
        + timedelta(days=days_until_weekday)
        + timedelta(
            weeks=occurrence - 1
        )
    )

    if result.month != month:
        raise ValueError(
            "Requested weekday occurrence does not "
            "exist in month."
        )

    return result


def _gregorian_easter_sunday(
    year: int,
) -> date:
    """Return Gregorian Easter Sunday using Meeus/Jones/Butcher.

    The function exists only to derive Holy Thursday and Good Friday
    for the project's projected MXMC calendar model.
    """

    a = year % 19
    b = year // 100
    c = year % 100

    d = b // 4
    e = b % 4

    f = (b + 8) // 25
    g = (b - f + 1) // 3

    h = (
        19 * a
        + b
        - d
        - g
        + 15
    ) % 30

    i = c // 4
    k = c % 4

    l = (
        32
        + 2 * e
        + 2 * i
        - h
        - k
    ) % 7

    m = (
        a
        + 11 * h
        + 22 * l
    ) // 451

    month = (
        h
        + l
        - 7 * m
        + 114
    ) // 31

    day = (
        (
            h
            + l
            - 7 * m
            + 114
        )
        % 31
    ) + 1

    return date(
        year,
        month,
        day,
    )


def projected_mxmc_holidays(
    year: int,
) -> frozenset[date]:
    """Generate recurring holidays for the synthetic MXMC model.

    IMPORTANT
    ---------
    This is a PROJECT CALENDAR MODEL.

    It is based on the recurring structure observed in the official
    Mexican financial-sector calendar, including the verified 2026
    calendar.

    It must not be represented as an official CNBV or CME calendar
    for future years.

    Real-market valuation must use a verified calendar source.
    """

    monday = 0

    easter_sunday = (
        _gregorian_easter_sunday(year)
    )

    holy_thursday = (
        easter_sunday
        - timedelta(days=3)
    )

    good_friday = (
        easter_sunday
        - timedelta(days=2)
    )

    holidays = {
        date(year, 1, 1),

        _nth_weekday_of_month(
            year=year,
            month=2,
            weekday=monday,
            occurrence=1,
        ),

        _nth_weekday_of_month(
            year=year,
            month=3,
            weekday=monday,
            occurrence=3,
        ),

        holy_thursday,
        good_friday,

        date(year, 5, 1),
        date(year, 9, 16),
        date(year, 11, 2),

        _nth_weekday_of_month(
            year=year,
            month=11,
            weekday=monday,
            occurrence=3,
        ),

        date(year, 12, 12),
        date(year, 12, 25),
    }

    return frozenset(holidays)


def build_projected_mxmc_calendar(
    *,
    start_year: int,
    end_year: int,
) -> BusinessCalendar:
    """Build long-horizon PROJECT MXMC calendar for synthetic testing.

    The returned calendar is suitable for deterministic synthetic
    experiments.

    It is not an authoritative future holiday calendar.
    """

    if end_year < start_year:
        raise ValueError(
            "End year cannot precede start year."
        )

    holidays: set[date] = set()

    for year in range(
        start_year,
        end_year + 1,
    ):
        holidays.update(
            projected_mxmc_holidays(year)
        )

    return BusinessCalendar.from_holidays(
        name="MXMC_PROJECTED",
        holidays=holidays,
    )