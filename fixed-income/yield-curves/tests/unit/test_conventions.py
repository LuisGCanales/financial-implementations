from datetime import date

import pytest

from yield_curves.conventions import (
    BusinessDayConvention,
    DayCountConvention,
    FTIIE_OIS_CONVENTIONS,
    act_360,
)


def test_canonical_ftiie_conventions() -> None:
    conventions = FTIIE_OIS_CONVENTIONS

    assert conventions.currency == "MXN"
    assert conventions.benchmark == "FTIIE"

    assert (
        conventions.floating_index
        == "MXN_TIIE_ON_OIS_COMPOUND"
    )

    assert conventions.calendar_id == "MXMC"

    assert (
        conventions.effective_date_lag_business_days
        == 2
    )

    assert (
        conventions.day_count
        == DayCountConvention.ACT_360
    )

    assert conventions.payment_frequency_days == 28
    assert conventions.calculation_frequency_days == 28
    assert conventions.reset_frequency_days == 28

    assert conventions.payment_lag_business_days == 2

    assert conventions.floating_index_tenor_days == 1

    assert (
        conventions.start_date_adjustment
        == BusinessDayConvention.FOLLOWING
    )

    assert (
        conventions.maturity_date_adjustment
        == BusinessDayConvention.FOLLOWING
    )


def test_act_360_for_exact_28_day_period() -> None:
    start = date(2026, 1, 1)
    end = date(2026, 1, 29)

    assert act_360(start, end) == pytest.approx(
        28 / 360
    )


def test_act_360_uses_actual_calendar_days() -> None:
    start = date(2026, 1, 1)
    end = date(2026, 2, 2)

    assert act_360(start, end) == pytest.approx(
        32 / 360
    )


def test_act_360_rejects_reversed_dates() -> None:
    with pytest.raises(
        ValueError,
        match="End date cannot precede",
    ):
        act_360(
            date(2026, 2, 1),
            date(2026, 1, 1),
        )