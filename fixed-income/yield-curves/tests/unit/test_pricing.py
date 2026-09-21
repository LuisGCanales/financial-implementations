from datetime import date
from pathlib import Path

import pytest

from yield_curves.calendars import (
    build_mxmc_calendar_from_csv,
)
from yield_curves.curves import (
    FlatContinuousZeroCurve,
)
from yield_curves.instruments import (
    build_ftiie_ois,
)
from yield_curves.pricing import (
    calculate_par_rate,
    project_floating_coupon,
    value_ftiie_ois,
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


@pytest.fixture
def sample_ois(mxmc_calendar):
    return build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        notional=1_000_000.0,
        calendar=mxmc_calendar,
    )


def test_projected_coupon_telescopes_to_curve_ratio(
    sample_ois,
) -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.07,
    )

    coupon = sample_ois.floating_leg[0]

    projected = project_floating_coupon(
        coupon=coupon,
        projection_curve=curve,
    )

    expected_growth = (
        curve.discount_factor(
            coupon.accrual_start_date
        )
        /
        curve.discount_factor(
            coupon.accrual_end_date
        )
    )

    assert (
        projected.compounded_growth_factor
        == pytest.approx(expected_growth)
    )

    assert (
        projected.compounded_return
        == pytest.approx(
            expected_growth - 1.0
        )
    )


def test_explicit_overnight_projection_telescopes(
    sample_ois,
) -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.07,
    )

    coupon = sample_ois.floating_leg[1]

    projected = project_floating_coupon(
        coupon=coupon,
        projection_curve=curve,
    )

    product = 1.0

    for observation in (
        projected.projected_observations
    ):
        product *= observation.growth_factor

    expected = (
        curve.discount_factor(
            coupon.accrual_start_date
        )
        /
        curve.discount_factor(
            coupon.accrual_end_date
        )
    )

    assert product == pytest.approx(
        expected
    )


def test_par_rate_produces_zero_npv(
    mxmc_calendar,
) -> None:
    base_ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.01,
        notional=1_000_000.0,
        calendar=mxmc_calendar,
    )

    curve = FlatContinuousZeroCurve(
        reference_date=base_ois.effective_date,
        rate=0.07,
    )

    par_rate = calculate_par_rate(
        ois=base_ois,
        projection_curve=curve,
        discount_curve=curve,
    )

    par_ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=par_rate,
        notional=1_000_000.0,
        calendar=mxmc_calendar,
    )

    valuation = value_ftiie_ois(
        ois=par_ois,
        projection_curve=curve,
        discount_curve=curve,
    )

    assert (
        valuation.npv_receive_float_pay_fixed
        == pytest.approx(
            0.0,
            abs=1e-8,
        )
    )


def test_par_rate_is_independent_of_notional(
    mxmc_calendar,
) -> None:
    small = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.01,
        notional=1.0,
        calendar=mxmc_calendar,
    )

    large = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.01,
        notional=100_000_000.0,
        calendar=mxmc_calendar,
    )

    curve = FlatContinuousZeroCurve(
        reference_date=small.effective_date,
        rate=0.07,
    )

    small_rate = calculate_par_rate(
        ois=small,
        projection_curve=curve,
        discount_curve=curve,
    )

    large_rate = calculate_par_rate(
        ois=large,
        projection_curve=curve,
        discount_curve=curve,
    )

    assert small_rate == pytest.approx(
        large_rate
    )


def test_projection_and_discount_curves_are_separable(
    sample_ois,
) -> None:
    projection_curve = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.08,
    )

    discount_curve = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.06,
    )

    multi_curve_rate = calculate_par_rate(
        ois=sample_ois,
        projection_curve=projection_curve,
        discount_curve=discount_curve,
    )

    same_curve_rate = calculate_par_rate(
        ois=sample_ois,
        projection_curve=discount_curve,
        discount_curve=discount_curve,
    )

    assert multi_curve_rate != pytest.approx(
        same_curve_rate
    )


def test_higher_projection_curve_increases_par_rate(
    sample_ois,
) -> None:
    discount_curve = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.06,
    )

    low_projection = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.05,
    )

    high_projection = FlatContinuousZeroCurve(
        reference_date=sample_ois.effective_date,
        rate=0.08,
    )

    low_rate = calculate_par_rate(
        ois=sample_ois,
        projection_curve=low_projection,
        discount_curve=discount_curve,
    )

    high_rate = calculate_par_rate(
        ois=sample_ois,
        projection_curve=high_projection,
        discount_curve=discount_curve,
    )

    assert high_rate > low_rate


def test_nonzero_floating_spread_fails_explicitly(
    mxmc_calendar,
) -> None:
    ois = build_ftiie_ois(
        trade_date=date(2026, 9, 15),
        maturity_date=date(2026, 12, 11),
        fixed_rate=0.07,
        floating_spread=0.001,
        calendar=mxmc_calendar,
    )

    curve = FlatContinuousZeroCurve(
        reference_date=ois.effective_date,
        rate=0.07,
    )

    with pytest.raises(
        NotImplementedError,
        match="zero floating spread",
    ):
        value_ftiie_ois(
            ois=ois,
            projection_curve=curve,
            discount_curve=curve,
        )