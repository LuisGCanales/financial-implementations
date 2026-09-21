from datetime import date
from pathlib import Path

import pytest

from yield_curves.calendars import (
    build_mxmc_calendar_from_csv,
)
from yield_curves.instruments import (
    build_ftiie_ois,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MXMC_2026_PATH = (
    PROJECT_ROOT
    / "data"
    / "calendars"
    / "mxmc_2026.csv"
)


@pytest.fixture
def mxmc_calendar():
    return build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )


def test_build_ftiie_ois(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    assert ois.calendar_id == "MXMC"

    # 16-Sep is an MXMC holiday.
    #
    # 17-Sep = T+1
    # 18-Sep = T+2
    assert ois.effective_date == date(
        2026,
        9,
        18,
    )

    assert ois.adjusted_maturity_date == date(
        2026,
        12,
        11,
    )

    assert ois.number_of_periods == 3


def test_three_28_day_periods(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    first, second, third = ois.fixed_leg

    assert first.accrual_start_date == date(
        2026,
        9,
        18,
    )
    assert first.accrual_end_date == date(
        2026,
        10,
        16,
    )

    assert second.accrual_start_date == date(
        2026,
        10,
        16,
    )
    assert second.accrual_end_date == date(
        2026,
        11,
        13,
    )

    assert third.accrual_start_date == date(
        2026,
        11,
        13,
    )
    assert third.accrual_end_date == date(
        2026,
        12,
        11,
    )

    for coupon in ois.fixed_leg:
        assert coupon.accrual_factor == pytest.approx(
            28 / 360
        )


def test_payment_dates_respect_mxmc_holidays(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    first, second, third = ois.fixed_leg

    assert first.payment_date == date(
        2026,
        10,
        20,
    )

    # 13-Nov is Friday.
    #
    # 16-Nov is an MXMC holiday.
    # 17-Nov = payment business day +1
    # 18-Nov = payment business day +2
    assert second.payment_date == date(
        2026,
        11,
        18,
    )

    assert third.payment_date == date(
        2026,
        12,
        15,
    )


def test_fixed_coupon_amount(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        notional=1_000_000.0,
        calendar=mxmc_calendar,
    )

    coupon = ois.fixed_leg[0]

    expected = (
        1_000_000
        * 0.07
        * 28
        / 360
    )

    assert coupon.amount == pytest.approx(
        expected
    )


def test_fixed_and_floating_legs_are_aligned(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    assert len(ois.fixed_leg) == len(
        ois.floating_leg
    )

    for fixed_coupon, floating_coupon in zip(
        ois.fixed_leg,
        ois.floating_leg,
    ):
        assert (
            fixed_coupon.period_number
            == floating_coupon.period_number
        )

        assert (
            fixed_coupon.accrual_start_date
            == floating_coupon.accrual_start_date
        )

        assert (
            fixed_coupon.accrual_end_date
            == floating_coupon.accrual_end_date
        )

        assert (
            fixed_coupon.payment_date
            == floating_coupon.payment_date
        )

        assert (
            fixed_coupon.accrual_factor
            == floating_coupon.accrual_factor
        )


def test_floating_observations_cover_each_coupon(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    for coupon in ois.floating_leg:
        observation_days = sum(
            observation.calendar_days
            for observation in coupon.observations
        )

        coupon_days = (
            coupon.accrual_end_date
            - coupon.accrual_start_date
        ).days

        assert observation_days == coupon_days


def test_real_mxmc_holidays_change_observation_count(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    observation_counts = [
        len(coupon.observations)
        for coupon in ois.floating_leg
    ]

    assert observation_counts == [
        20,
        19,
        19,
    ]


def test_floating_spread_defaults_to_zero(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        calendar=mxmc_calendar,
    )

    assert all(
        coupon.spread == 0.0
        for coupon in ois.floating_leg
    )


def test_non_positive_notional_is_rejected(
    mxmc_calendar,
) -> None:
    with pytest.raises(
        ValueError,
        match="Notional must be positive",
    ):
        build_ftiie_ois(
            trade_date=date(2026, 9, 15),
            maturity_date=date(2026, 12, 11),
            fixed_rate=0.07,
            notional=0.0,
            calendar=mxmc_calendar,
        )