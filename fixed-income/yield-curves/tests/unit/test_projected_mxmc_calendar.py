from datetime import date
from pathlib import Path

from yield_curves.calendars import (
    build_mxmc_calendar_from_csv,
    build_projected_mxmc_calendar,
    projected_mxmc_holidays,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MXMC_2026_PATH = (
    PROJECT_ROOT
    / "data"
    / "calendars"
    / "mxmc_2026.csv"
)


def test_projected_2026_matches_verified_2026_holidays() -> None:
    verified = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    projected = projected_mxmc_holidays(
        2026
    )

    assert projected == verified.holidays


def test_projected_calendar_covers_long_horizon() -> None:
    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    assert calendar.name == "MXMC_PROJECTED"

    assert date(
        2056,
        9,
        16,
    ) in calendar.holidays


def test_projected_2026_holy_thursday() -> None:
    holidays = projected_mxmc_holidays(
        2026
    )

    assert date(
        2026,
        4,
        2,
    ) in holidays


def test_projected_2026_good_friday() -> None:
    holidays = projected_mxmc_holidays(
        2026
    )

    assert date(
        2026,
        4,
        3,
    ) in holidays


def test_projected_mxmc_independence_day() -> None:
    calendar = build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )

    assert not calendar.is_business_day(
        date(2040, 9, 16)
    )