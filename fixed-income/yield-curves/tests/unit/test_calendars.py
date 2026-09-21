from datetime import date

from yield_curves.calendars import BusinessCalendar
from yield_curves.conventions import (
    BusinessDayConvention,
)


def test_weekend_is_not_business_day() -> None:
    calendar = BusinessCalendar(name="TEST")

    saturday = date(2026, 9, 19)
    sunday = date(2026, 9, 20)
    monday = date(2026, 9, 21)

    assert not calendar.is_business_day(saturday)
    assert not calendar.is_business_day(sunday)
    assert calendar.is_business_day(monday)


def test_explicit_holiday_is_not_business_day() -> None:
    holiday = date(2026, 9, 21)

    calendar = BusinessCalendar.from_holidays(
        name="TEST",
        holidays=[holiday],
    )

    assert not calendar.is_business_day(holiday)


def test_following_adjustment_skips_weekend() -> None:
    calendar = BusinessCalendar(name="TEST")

    saturday = date(2026, 9, 19)

    adjusted = calendar.adjust(
        saturday,
        BusinessDayConvention.FOLLOWING,
    )

    assert adjusted == date(2026, 9, 21)


def test_following_adjustment_skips_holiday() -> None:
    monday_holiday = date(2026, 9, 21)

    calendar = BusinessCalendar.from_holidays(
        name="TEST",
        holidays=[monday_holiday],
    )

    saturday = date(2026, 9, 19)

    adjusted = calendar.following(saturday)

    assert adjusted == date(2026, 9, 22)


def test_preceding_adjustment() -> None:
    calendar = BusinessCalendar(name="TEST")

    sunday = date(2026, 9, 20)

    assert (
        calendar.preceding(sunday)
        == date(2026, 9, 18)
    )


def test_add_positive_business_days() -> None:
    calendar = BusinessCalendar(name="TEST")

    friday = date(2026, 9, 18)

    assert (
        calendar.add_business_days(friday, 2)
        == date(2026, 9, 22)
    )


def test_add_negative_business_days() -> None:
    calendar = BusinessCalendar(name="TEST")

    monday = date(2026, 9, 21)

    assert (
        calendar.add_business_days(monday, -1)
        == date(2026, 9, 18)
    )


def test_zero_business_day_offset_does_not_adjust() -> None:
    calendar = BusinessCalendar(name="TEST")

    saturday = date(2026, 9, 19)

    assert (
        calendar.add_business_days(saturday, 0)
        == saturday
    )