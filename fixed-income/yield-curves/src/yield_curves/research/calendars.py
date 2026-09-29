"""Projected holiday model for synthetic scenarios."""

from datetime import date, timedelta
from ..calendars import BusinessCalendar, CalendarProvenance, CalendarSource

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
        coverage_start=date(start_year, 1, 1),
        coverage_end=date(end_year, 12, 31),
        provenance=CalendarProvenance(
            source="projected_mxmc_holidays",
            kind=CalendarSource.PROJECTED,
        ),
    )