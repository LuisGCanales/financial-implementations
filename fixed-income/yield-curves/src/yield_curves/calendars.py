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
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from .conventions import BusinessDayConvention


WEEKEND_DAYS = frozenset({5, 6})
# Python weekday:
# Monday = 0
# ...
# Saturday = 5
# Sunday = 6


class CalendarCoverageError(ValueError):
    """Requested dates exceed declared coverage, or coverage is unspecified."""


class CalendarSource(StrEnum):
    PROVIDED = "PROVIDED"
    PROJECTED = "PROJECTED"


@dataclass(frozen=True, slots=True)
class CalendarProvenance:
    """Source declaration; PROVIDED does not imply independently verified data."""

    source: str
    kind: CalendarSource
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Calendar source must not be empty.")
        object.__setattr__(self, "kind", CalendarSource(self.kind))


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
    coverage_start, coverage_end
        Inclusive bounds. Both may be omitted for legacy calendars; operational
        input checks require declared coverage. Date operations enforce bounds
        whenever they are supplied, including business-day shifts.
    provenance
        Optional source declaration and file fingerprint. This does not certify
        completeness or authenticity of the holiday source.
    """

    name: str
    holidays: frozenset[date] = field(default_factory=frozenset)
    weekend_days: frozenset[int] = WEEKEND_DAYS

    coverage_start: date | None = None
    coverage_end: date | None = None
    provenance: CalendarProvenance | None = None

    def __post_init__(self) -> None:
        if (self.coverage_start is None) != (self.coverage_end is None):
            raise ValueError("Calendar coverage requires both start and end dates.")
        if self.coverage_start is not None and self.coverage_end < self.coverage_start:
            raise ValueError("Calendar coverage end cannot precede start.")

    def _check_coverage(self, value: date) -> None:
        if self.coverage_start is not None and not (
            self.coverage_start <= value <= self.coverage_end
        ):
            raise CalendarCoverageError(
                f"{self.name}: {value} is outside calendar coverage "
                f"[{self.coverage_start}, {self.coverage_end}]."
            )

    def require_coverage(self, start: date, end: date | None = None) -> None:
        """Require explicit inclusive coverage for operational input checks."""
        end = start if end is None else end
        if end < start:
            raise ValueError("Requested coverage end cannot precede start.")
        if self.coverage_start is None:
            raise CalendarCoverageError(f"{self.name}: calendar coverage is unspecified.")
        self._check_coverage(start)
        self._check_coverage(end)

    @classmethod
    def from_holidays(
        cls,
        name: str,
        holidays: Iterable[date],
        *,
        coverage_start: date | None = None,
        coverage_end: date | None = None,
        provenance: CalendarProvenance | None = None,
    ) -> "BusinessCalendar":
        """Construct a calendar from an iterable of holiday dates."""

        return cls(
            name=name,
            holidays=frozenset(holidays),
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            provenance=provenance,
        )

    def is_weekend(self, value: date) -> bool:
        """Return True when date falls on configured weekend."""

        self._check_coverage(value)
        return value.weekday() in self.weekend_days

    def is_holiday(self, value: date) -> bool:
        """Return True when date appears in explicit holiday set."""

        self._check_coverage(value)
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

        self._check_coverage(value)
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

        self._check_coverage(value)
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

    return _parse_holidays_csv(
        Path(path).read_text(encoding="utf-8-sig"), date_column=date_column
    )


def _parse_holidays_csv(text: str, *, date_column: str) -> frozenset[date]:
    reader = csv.DictReader(io.StringIO(text))
    if date_column not in (reader.fieldnames or []):
        raise ValueError(f"CSV must contain column '{date_column}'.")
    holidays: set[date] = set()
    for row in reader:
        raw_value = row[date_column].strip()
        if raw_value:
            holidays.add(date.fromisoformat(raw_value))
    return frozenset(holidays)


def build_mxmc_calendar(
    holidays: Iterable[date],
    *,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    provenance: CalendarProvenance | None = None,
) -> BusinessCalendar:
    """Construct the project MXMC calendar from supplied holiday data."""

    return BusinessCalendar.from_holidays(
        name="MXMC",
        holidays=holidays,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        provenance=provenance,
    )
    
    
def build_mxmc_calendar_from_csv(
    path: str | Path,
    *,
    coverage_start: date | None = None,
    coverage_end: date | None = None,
    source: str | None = None,
) -> BusinessCalendar:
    """Load provided holidays; coverage is declared, never inferred from holidays."""
    path = Path(path).resolve()
    raw = path.read_bytes()
    # Parse the same bytes that are fingerprinted.
    holidays = _parse_holidays_csv(raw.decode("utf-8-sig"), date_column="date")
    return build_mxmc_calendar(
        holidays,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        provenance=CalendarProvenance(
            source=str(path) if source is None else source,
            kind=CalendarSource.PROVIDED,
            sha256=hashlib.sha256(raw).hexdigest(),
        ),
    )


