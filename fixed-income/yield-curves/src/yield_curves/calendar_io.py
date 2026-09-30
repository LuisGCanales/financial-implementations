"""Filesystem adapters for explicitly supplied holiday calendars."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import date
from pathlib import Path

from .calendars import (
    BusinessCalendar,
    CalendarProvenance,
    CalendarSource,
    build_mxmc_calendar,
)


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
