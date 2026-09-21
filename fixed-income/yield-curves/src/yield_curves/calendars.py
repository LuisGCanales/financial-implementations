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