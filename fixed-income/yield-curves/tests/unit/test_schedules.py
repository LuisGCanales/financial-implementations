from datetime import date

import pytest

from yield_curves.calendars import BusinessCalendar
from yield_curves.schedules import (
    calculate_effective_date,
    generate_ois_schedule,
)


def test_effective_date_is_t_plus_two_business_days() -> None:
    calendar = BusinessCalendar(name="TEST")

    trade_date = date(2026, 9, 18)  # Friday

    effective_date = calculate_effective_date(
        trade_date,
        calendar,
    )

    assert effective_date == date(2026, 9, 22)


def test_effective_date_skips_explicit_holiday() -> None:
    monday_holiday = date(2026, 9, 21)

    calendar = BusinessCalendar.from_holidays(
        name="TEST",
        holidays=[monday_holiday],
    )

    trade_date = date(2026, 9, 18)

    effective_date = calculate_effective_date(
        trade_date,
        calendar,
    )

    # Monday is holiday.
    # Tuesday = T+1
    # Wednesday = T+2
    assert effective_date == date(2026, 9, 23)


def test_two_exact_28_day_periods() -> None:
    calendar = BusinessCalendar(name="TEST")

    effective = date(2026, 9, 18)
    maturity = date(2026, 11, 13)

    schedule = generate_ois_schedule(
        effective_date=effective,
        maturity_date=maturity,
        calendar=calendar,
    )

    assert schedule.number_of_periods == 2

    first, second = schedule.periods

    assert first.start_date == date(2026, 9, 18)
    assert first.end_date == date(2026, 10, 16)

    assert second.start_date == date(2026, 10, 16)
    assert second.end_date == date(2026, 11, 13)

    assert first.accrual_factor == pytest.approx(
        28 / 360
    )

    assert second.accrual_factor == pytest.approx(
        28 / 360
    )


def test_payment_date_is_two_business_days_after_end() -> None:
    calendar = BusinessCalendar(name="TEST")

    effective = date(2026, 9, 18)
    maturity = date(2026, 10, 16)

    schedule = generate_ois_schedule(
        effective_date=effective,
        maturity_date=maturity,
        calendar=calendar,
    )

    period = schedule.periods[0]

    # Friday 16 Oct + 2 business days
    # Monday = +1
    # Tuesday = +2
    assert period.payment_date == date(
        2026,
        10,
        20,
    )


def test_holiday_adjustment_preserves_contiguous_periods() -> None:
    # 2026-10-16 is the first unadjusted 28D boundary.
    boundary_holiday = date(2026, 10, 16)

    calendar = BusinessCalendar.from_holidays(
        name="TEST",
        holidays=[boundary_holiday],
    )

    effective = date(2026, 9, 18)
    maturity = date(2026, 11, 13)

    schedule = generate_ois_schedule(
        effective_date=effective,
        maturity_date=maturity,
        calendar=calendar,
    )

    first, second = schedule.periods

    # Friday 16 Oct is holiday,
    # so FOLLOWING -> Monday 19 Oct.
    assert first.end_date == date(
        2026,
        10,
        19,
    )

    assert second.start_date == date(
        2026,
        10,
        19,
    )

    assert first.end_date == second.start_date

    # Adjusted periods no longer both contain exactly 28 days.
    assert first.accrual_factor == pytest.approx(
        31 / 360
    )

    assert second.accrual_factor == pytest.approx(
        25 / 360
    )


def test_final_stub_is_supported_explicitly() -> None:
    calendar = BusinessCalendar(name="TEST")

    effective = date(2026, 9, 18)

    # 35 calendar days later:
    # one full 28D period + one 7D final stub.
    maturity = date(2026, 10, 23)

    schedule = generate_ois_schedule(
        effective_date=effective,
        maturity_date=maturity,
        calendar=calendar,
    )

    assert schedule.number_of_periods == 2

    first, second = schedule.periods

    assert first.unadjusted_end_date == date(
        2026,
        10,
        16,
    )

    assert second.unadjusted_end_date == maturity

    assert first.accrual_factor == pytest.approx(
        28 / 360
    )

    assert second.accrual_factor == pytest.approx(
        7 / 360
    )


def test_maturity_must_follow_effective_date() -> None:
    calendar = BusinessCalendar(name="TEST")

    with pytest.raises(
        ValueError,
        match="Maturity date must be after",
    ):
        generate_ois_schedule(
            effective_date=date(2026, 9, 18),
            maturity_date=date(2026, 9, 18),
            calendar=calendar,
        )