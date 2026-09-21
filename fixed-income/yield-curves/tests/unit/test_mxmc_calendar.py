from datetime import date
from pathlib import Path

from yield_curves.calendars import (
    build_mxmc_calendar_from_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MXMC_2026_PATH = (
    PROJECT_ROOT
    / "data"
    / "calendars"
    / "mxmc_2026.csv"
)


def test_mxmc_2026_loads() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.name == "MXMC"


def test_independence_day_is_holiday() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert not calendar.is_business_day(
        date(2026, 9, 16)
    )


def test_days_around_independence_day() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.is_business_day(
        date(2026, 9, 15)
    )

    assert not calendar.is_business_day(
        date(2026, 9, 16)
    )

    assert calendar.is_business_day(
        date(2026, 9, 17)
    )


def test_bmv_cnbv_bank_employee_day_is_holiday() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.is_holiday(
        date(2026, 12, 12)
    )


def test_t_plus_two_skips_independence_day() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    trade_date = date(2026, 9, 15)

    result = calendar.add_business_days(
        trade_date,
        2,
    )

    # 16-Sep is a holiday.
    # 17-Sep = T+1
    # 18-Sep = T+2
    assert result == date(2026, 9, 18)