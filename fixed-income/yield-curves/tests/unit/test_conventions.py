from dataclasses import fields, replace
from datetime import date

import pytest

from yield_curves.conventions import (
    BusinessDayConvention,
    CompoundingMethod,
    DateRelativeTo,
    DayType,
    FTiieOISConventions,
    RollConvention,
    SpreadTreatment,
    DayCountConvention,
    FTIIE_OIS_CONVENTIONS,
    act_360,
)

from yield_curves.calendars import BusinessCalendar
from yield_curves.instruments import build_ftiie_ois
from yield_curves.observations import generate_overnight_observations
from yield_curves.schedules import calculate_effective_date, generate_ois_schedule


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

# Explicit contract examples, independent of the implementation's defaults.
CORE_V1_FIELDS = [
    ('currency', 'MXN', 'USD'),
    ('benchmark', 'FTIIE', 'OTHER'),
    ('floating_index', 'MXN_TIIE_ON_OIS_COMPOUND', 'OTHER'),
    ('calendar_id', 'MXMC', 'OTHER'),
    ('effective_date_lag_business_days', 2, 1),
    ('day_count', DayCountConvention.ACT_360, 'ACT_365'),
    ('payment_frequency_days', 28, 56),
    ('calculation_frequency_days', 28, 14),
    ('reset_frequency_days', 28, 56),
    ('roll_convention', RollConvention.NONE, 'EOM'),
    ('start_date_adjustment', BusinessDayConvention.FOLLOWING, BusinessDayConvention.PRECEDING),
    ('maturity_date_adjustment', BusinessDayConvention.FOLLOWING, BusinessDayConvention.PRECEDING),
    ('calculation_period_adjustment', BusinessDayConvention.FOLLOWING, BusinessDayConvention.NONE),
    ('payment_relative_to', DateRelativeTo.END_PERIOD, 'START_PERIOD'),
    ('payment_adjustment', BusinessDayConvention.FOLLOWING, BusinessDayConvention.NONE),
    ('payment_lag_business_days', 2, 0),
    ('reset_relative_to', DateRelativeTo.END_PERIOD, 'START_PERIOD'),
    ('reset_adjustment', BusinessDayConvention.FOLLOWING, BusinessDayConvention.PRECEDING),
    ('floating_index_tenor_days', 1, 2),
    ('fixing_offset_business_days', 0, 1),
    ('fixing_day_type', DayType.BUSINESS, DayType.CALENDAR),
    ('fixing_adjustment', BusinessDayConvention.PRECEDING, BusinessDayConvention.FOLLOWING),
    ('compounding_method', CompoundingMethod.ISDA_STANDARD, 'SIMPLE'),
    ('spread_treatment', SpreadTreatment.SPREAD_EXCLUSIVE, 'SPREAD_INCLUSIVE'),
    ('floating_spread', 0.0, 0.001),
    ('calibration_notional', 1.0, 100.0),
]


def test_closed_profile_covers_every_field():
    assert {field.name for field in fields(FTiieOISConventions)} == {
        name for name, _, _ in CORE_V1_FIELDS
    }
    explicit = FTiieOISConventions(**{
        name: canonical for name, canonical, _ in CORE_V1_FIELDS
    })
    assert explicit == FTIIE_OIS_CONVENTIONS


@pytest.mark.parametrize('name,canonical,unsupported', CORE_V1_FIELDS)
def test_every_noncanonical_field_is_rejected(name, canonical, unsupported):
    with pytest.raises(ValueError, match=name):
        replace(FTIIE_OIS_CONVENTIONS, **{name: unsupported})


@pytest.mark.parametrize('entrypoint', ['effective', 'schedule', 'observations', 'instrument', 'direct_instrument'])
@pytest.mark.parametrize('name,canonical,unsupported', CORE_V1_FIELDS)
def test_direct_callers_validate_profile(entrypoint, name, canonical, unsupported):
    # Model a profile restored without __init__: boundaries must still reject it.
    profile = FTiieOISConventions()
    object.__setattr__(profile, name, unsupported)
    calendar = BusinessCalendar(name='MXMC_PROJECTED')
    start, end = date(2026, 9, 18), date(2026, 10, 16)
    ois = build_ftiie_ois(
        trade_date=start, maturity_date=end, fixed_rate=0.07, calendar=calendar,
    )
    with pytest.raises(ValueError, match=name):
        if entrypoint == 'effective':
            calculate_effective_date(start, calendar, profile)
        elif entrypoint == 'schedule':
            generate_ois_schedule(effective_date=start, maturity_date=end,
                                  calendar=calendar, conventions=profile)
        elif entrypoint == 'observations':
            generate_overnight_observations(period_start_date=start, period_end_date=end,
                                            calendar=calendar, conventions=profile)
        elif entrypoint == 'instrument':
            build_ftiie_ois(trade_date=start, maturity_date=end, fixed_rate=0.07,
                           calendar=calendar, conventions=profile)
        else:
            replace(ois, conventions=profile)


@pytest.mark.parametrize('name,value', [
    ('floating_spread', float('nan')),
    ('calibration_notional', float('inf')),
    ('calibration_notional', float('nan')),
    ('floating_index_tenor_days', True),
    ('calculation_frequency_days', 28.0),
    ('fixing_day_type', 'BUSINESS'),
])
def test_invalid_profile_types_and_nonfinite_values(name, value):
    with pytest.raises(ValueError, match=name):
        FTiieOISConventions(**{name: value})
