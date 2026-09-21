from datetime import date
from pathlib import Path

import pytest

from yield_curves.calendars import (
    BusinessCalendar,
    build_mxmc_calendar_from_csv,
)
from yield_curves.observations import (
    compound_overnight_fixings,
    generate_overnight_observations,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MXMC_2026_PATH = (
    PROJECT_ROOT
    / "data"
    / "calendars"
    / "mxmc_2026.csv"
)


def test_weekend_is_carried_by_friday_fixing() -> None:
    calendar = BusinessCalendar(name="TEST")

    observations = generate_overnight_observations(
        period_start_date=date(2026, 9, 18),
        period_end_date=date(2026, 9, 21),
        calendar=calendar,
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.fixing_date == date(
        2026,
        9,
        18,
    )

    assert observation.accrual_start_date == date(
        2026,
        9,
        18,
    )

    assert observation.accrual_end_date == date(
        2026,
        9,
        21,
    )

    assert observation.calendar_days == 3

    assert observation.accrual_factor == pytest.approx(
        3 / 360
    )


def test_mxmc_holiday_creates_two_day_observation() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    observations = generate_overnight_observations(
        period_start_date=date(2026, 9, 15),
        period_end_date=date(2026, 9, 17),
        calendar=calendar,
    )

    assert len(observations) == 1

    observation = observations[0]

    assert observation.fixing_date == date(
        2026,
        9,
        15,
    )

    assert observation.accrual_end_date == date(
        2026,
        9,
        17,
    )

    assert observation.calendar_days == 2

    assert observation.accrual_factor == pytest.approx(
        2 / 360
    )


def test_mixed_holiday_and_weekend_period() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    observations = generate_overnight_observations(
        period_start_date=date(2026, 9, 15),
        period_end_date=date(2026, 9, 21),
        calendar=calendar,
    )

    assert len(observations) == 3

    first, second, third = observations

    # Independence Day.
    assert first.fixing_date == date(2026, 9, 15)
    assert first.calendar_days == 2

    # Normal overnight business-day interval.
    assert second.fixing_date == date(2026, 9, 17)
    assert second.calendar_days == 1

    # Friday rate carries across the weekend.
    assert third.fixing_date == date(2026, 9, 18)
    assert third.calendar_days == 3

    assert sum(
        observation.calendar_days
        for observation in observations
    ) == 6


def test_observations_cover_full_coupon_period() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    start = date(2026, 9, 22)
    end = date(2026, 10, 20)

    observations = generate_overnight_observations(
        period_start_date=start,
        period_end_date=end,
        calendar=calendar,
    )

    total_days = sum(
        observation.calendar_days
        for observation in observations
    )

    assert total_days == (end - start).days
    assert total_days == 28


def test_constant_rate_compounding() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    observations = generate_overnight_observations(
        period_start_date=date(2026, 9, 15),
        period_end_date=date(2026, 9, 21),
        calendar=calendar,
    )

    rate = 0.07

    fixings = {
        observation.fixing_date: rate
        for observation in observations
    }

    result = compound_overnight_fixings(
        observations=observations,
        fixings=fixings,
    )

    expected_growth = (
        (1 + rate * 2 / 360)
        * (1 + rate * 1 / 360)
        * (1 + rate * 3 / 360)
    )

    assert result.growth_factor == pytest.approx(
        expected_growth
    )

    assert result.compounded_return == pytest.approx(
        expected_growth - 1
    )

    assert result.calendar_days == 6

    assert result.period_accrual_factor == pytest.approx(
        6 / 360
    )

    assert result.annualized_rate == pytest.approx(
        (expected_growth - 1)
        / (6 / 360)
    )


def test_missing_fixing_fails_explicitly() -> None:
    calendar = BusinessCalendar(name="TEST")

    observations = generate_overnight_observations(
        period_start_date=date(2026, 9, 18),
        period_end_date=date(2026, 9, 21),
        calendar=calendar,
    )

    with pytest.raises(
        KeyError,
        match="Missing fixing",
    ):
        compound_overnight_fixings(
            observations=observations,
            fixings={},
        )


def test_non_business_period_start_is_rejected() -> None:
    calendar = BusinessCalendar(name="TEST")

    with pytest.raises(
        ValueError,
        match="Period start date must be a business day",
    ):
        generate_overnight_observations(
            period_start_date=date(2026, 9, 19),
            period_end_date=date(2026, 9, 21),
            calendar=calendar,
        )