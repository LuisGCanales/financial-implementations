"""P09 characterization: deterministic dates/values, without calibration fixtures."""

from datetime import date, timedelta
from math import sqrt

import pytest

from yield_curves.conventions import act_360
from yield_curves.curves import (
    CubicContinuousZeroCurve, LinearContinuousZeroCurve, PchipContinuousZeroCurve,
)
from yield_curves.diagnostics import build_forward_observations
from yield_curves.research.global_sensitivity import (
    _calculate_forward_sensitivity, _forward_start_dates,
    calculate_forward_sensitivity_locality,
)
from yield_curves.research.recovery import (
    RecoveryHorizon, _build_date_grid, calculate_horizon_recovery_metrics,
    calculate_recovery_metrics,
)
from yield_curves.research.sensitivity import (
    _build_forward_start_dates, _summarize_forward_changes,
)


REFERENCE = date(2026, 1, 1)


def dates(*offsets):
    return tuple(REFERENCE + timedelta(days=offset) for offset in offsets)


class RecordingCurve:
    reference_date = REFERENCE

    def __init__(self, bump=0.0):
        self.bump = bump
        self.df_dates = []
        self.zero_dates = []
        self.forward_dates = []

    def discount_factor(self, target_date):
        self.df_dates.append(target_date)
        return 1.0 + self.bump

    def zero_rate(self, target_date):
        self.zero_dates.append(target_date)
        return 0.05 + self.bump

    def forward_rate(self, start_date, end_date):
        self.forward_dates.append((start_date, end_date))
        return 0.05 + self.bump * (1 + (start_date - REFERENCE).days)


def forward_grid(caller, horizon, period=3, step=7):
    kwargs = dict(reference_date=REFERENCE, forward_period_days=period,
                  grid_step_days=step)
    last = REFERENCE + timedelta(days=horizon)
    if caller == "diagnostics":
        return tuple(item.start_date for item in build_forward_observations(
            curve=RecordingCurve(), last_supported_date=last,
            forward_period_days=period, grid_step_days=step,
        ))
    if caller == "sensitivity":
        return _build_forward_start_dates(last_supported_date=last, **kwargs)
    return _forward_start_dates(last_date=last, **kwargs)


@pytest.mark.parametrize("horizon,step,expected", [
    (14, 7, (0, 7, 14)), (15, 7, (0, 7, 14, 15)),
    (0, 7, (0,)), (1, 7, (0, 1)), (7, 7, (0, 7)), (6, 7, (0, 6)),
])
def test_inclusive_grid_endpoints(horizon, step, expected):
    actual = _build_date_grid(start_date=REFERENCE, end_date=dates(horizon)[0],
                              step_days=step)
    assert type(actual) is tuple
    assert actual == dates(*expected)
    assert all(type(item) is date for item in actual)


@pytest.mark.parametrize("caller", ["diagnostics", "sensitivity", "global"])
@pytest.mark.parametrize("horizon,period,step,expected", [
    (17, 3, 7, (0, 7, 14)), (18, 3, 7, (0, 7, 14)),
    (1, 1, 7, (0,)), (7, 3, 7, (0,)), (6, 3, 7, (0,)),
    (7, 7, 7, (0,)), (14, 7, 7, (0, 7)),
])
def test_forward_grid_requires_complete_period(caller, horizon, period, step, expected):
    actual = forward_grid(caller, horizon, period, step)
    assert type(actual) is tuple
    assert actual == dates(*expected)
    assert all(item + timedelta(days=period) <= dates(horizon)[0] for item in actual)


@pytest.mark.parametrize("step", [0, -1])
def test_inclusive_grid_rejects_nonpositive_step(step):
    with pytest.raises(ValueError, match="^Grid step must be positive\\.$"):
        _build_date_grid(start_date=REFERENCE, end_date=REFERENCE, step_days=step)


def test_inclusive_grid_rejects_reversed_dates():
    with pytest.raises(ValueError, match="^End date cannot precede start date\\.$"):
        _build_date_grid(start_date=REFERENCE, end_date=dates(-1)[0], step_days=7)


@pytest.mark.parametrize("caller", ["diagnostics", "sensitivity", "global"])
@pytest.mark.parametrize("step", [0, -1])
def test_forward_grid_step_guard_precedes_horizon_guard(caller, step):
    with pytest.raises(ValueError, match="^Grid step must be positive\\.$"):
        forward_grid(caller, -1, step=step)


@pytest.mark.parametrize("caller", ["diagnostics", "sensitivity", "global"])
@pytest.mark.parametrize("period", [0, -1])
def test_forward_grid_period_guard_precedes_step_guard(caller, period):
    with pytest.raises(ValueError, match="^Forward period must be positive\\.$"):
        forward_grid(caller, -1, period=period, step=0)


@pytest.mark.parametrize("horizon", [-1, 0, 2])
@pytest.mark.parametrize("caller", ["diagnostics", "sensitivity", "global"])
def test_forward_grid_preserves_horizon_errors(caller, horizon):
    messages = {
        "diagnostics": "Curve horizon is too short for requested forward period.",
        "sensitivity": "Curve horizon is too short for the requested forward period.",
        "global": ("Last supported date must follow the reference date." if horizon <= 0
                   else "Curve horizon is shorter than the forward period."),
    }
    with pytest.raises(ValueError) as error:
        forward_grid(caller, horizon)
    assert str(error.value) == messages[caller]


def test_diagnostics_preserves_dates_times_rates_and_evaluation_order():
    curve = RecordingCurve(bump=0.001)
    observations = build_forward_observations(
        curve=curve, last_supported_date=dates(18)[0],
        forward_period_days=3, grid_step_days=7,
    )
    assert type(observations) is tuple
    assert curve.forward_dates == list(zip(dates(0, 7, 14), dates(3, 10, 17)))
    assert tuple(item.start_time for item in observations) == (0.0, 7 / 360.0, 14 / 360.0)
    assert tuple(item.end_time for item in observations) == (3 / 360.0, 10 / 360.0, 17 / 360.0)
    assert tuple(item.rate for item in observations) == (0.051000000000000004, 0.058, 0.065)


@pytest.mark.parametrize("segmented", [False, True])
def test_recovery_includes_off_grid_terminal_and_last_forward_start(segmented):
    true, recovered = RecordingCurve(), RecordingCurve(0.001)
    kwargs = dict(true_curve=true, recovered_curve=recovered,
                  last_supported_date=dates(18)[0], dense_grid_step_days=7,
                  forward_period_days=3)
    if segmented:
        results = calculate_horizon_recovery_metrics(
            horizons=(RecoveryHorizon("test", REFERENCE, dates(18)[0], True),), **kwargs,
        )
        assert type(results) is tuple
        result = results[0]
        expected_df_dates = dates(0, 7, 14, 18)
    else:
        result = calculate_recovery_metrics(pillar_dates=dates(18), **kwargs)
        expected_df_dates = dates(18, 0, 7, 14, 18)
    for curve in (true, recovered):
        assert curve.df_dates == list(expected_df_dates)
        assert curve.zero_dates == list(dates(7, 14, 18))
        assert curve.forward_dates == list(zip(dates(0, 7, 14, 15), dates(3, 10, 17, 18)))
    assert result.dense_df_absolute.observation_count == 4
    assert result.zero_rate_bp.observation_count == 3
    assert result.forward_28d_bp.observation_count == 4
    assert result.forward_28d_bp.bias == pytest.approx(100.0)
    assert result.forward_28d_bp.rmse == pytest.approx(sqrt((10**2 + 80**2 + 150**2 + 160**2) / 4))
    assert result.forward_28d_bp.max_abs_error_date == dates(15)[0]


def test_sensitivity_callers_keep_regular_grid_values():
    grid = forward_grid("sensitivity", 18)
    base, plus, minus = RecordingCurve(), RecordingCurve(0.0001), RecordingCurve(-0.0001)
    summary = _summarize_forward_changes(
        base_curve=base, shocked_curve=plus, forward_start_dates=grid, forward_period_days=3,
    )
    assert summary.observation_count == 3
    assert summary.bias_bp == pytest.approx(8.0)
    response = _calculate_forward_sensitivity(
        base_curve=base, plus_curve=plus, minus_curve=minus, dates=grid,
        bump_bp=1.0, forward_period_days=3,
    )
    assert type(response.observations) is tuple
    assert tuple(item.start_date for item in response.observations) == dates(0, 7, 14)
    assert tuple(item.end_date for item in response.observations) == dates(3, 10, 17)
    assert tuple(item.central_sensitivity_bp_per_bp for item in response.observations) == pytest.approx((1.0, 8.0, 15.0))
    assert response.sensitivity_bias == pytest.approx(8.0)
    assert response.sensitivity_rmse == pytest.approx(sqrt((1 + 64 + 225) / 3))
    assert response.maximum_abs_sensitivity_date == dates(14)[0]


@pytest.mark.parametrize("offset", [0, 1, 360])
def test_act360_nonnegative_duration(offset):
    result = act_360(REFERENCE, dates(offset)[0])
    assert type(result) is float
    assert result == offset / 360.0


def test_act360_rejects_negative_duration():
    with pytest.raises(ValueError, match="^End date cannot precede start date\\.$"):
        act_360(REFERENCE, dates(-1)[0])


@pytest.mark.parametrize("curve_type", [LinearContinuousZeroCurve, CubicContinuousZeroCurve,
                                        PchipContinuousZeroCurve])
def test_internal_signed_curve_time_does_not_widen_public_domain(curve_type):
    curve = curve_type(reference_date=REFERENCE, node_dates=dates(7, 14),
                       discount_factors=(0.99, 0.98))
    assert type(curve._time(dates(-1)[0])) is float
    assert curve._time(dates(-1)[0]) == -1 / 360.0
    assert type(curve.node_times) is tuple
    assert curve.node_times == (7 / 360.0, 14 / 360.0)
    for target in dates(-1, 15):
        with pytest.raises(ValueError):
            curve.discount_factor(target)


@pytest.mark.parametrize("sequence", [list, tuple])
def test_locality_keeps_signed_center_and_nonnegative_date_coordinates(sequence):
    result = calculate_forward_sensitivity_locality(
        reference_date=REFERENCE, shock_pillar_date=dates(360)[0],
        forward_start_dates=sequence(dates(0, 180)), sensitivities_bp_per_bp=sequence([1.0, 1.0]),
    )
    assert result.shock_pillar_years == 1.0
    assert result.weighted_center_years == 0.25
    assert result.center_offset_from_shock_years == -0.75
    assert result.weighted_spread_years == 0.25


@pytest.mark.parametrize("shock,starts,message", [
    (-1, (0,), "Shock pillar date cannot precede the curve reference date."),
    (0, (-1,), "Forward-start dates cannot precede the curve reference date."),
])
def test_locality_preserves_date_guards(shock, starts, message):
    with pytest.raises(ValueError) as error:
        calculate_forward_sensitivity_locality(
            reference_date=REFERENCE, shock_pillar_date=dates(shock)[0],
            forward_start_dates=dates(*starts), sensitivities_bp_per_bp=[1.0],
        )
    assert str(error.value) == message


@pytest.mark.parametrize("horizon,expected", [(14, (0, 7, 14)), (15, (0, 7, 14)), (0, (0,))])
def test_shared_forward_iterator_contract(horizon, expected):
    from yield_curves.date_grids import iter_forward_start_dates

    starts = iter_forward_start_dates(reference_date=REFERENCE,
                                      last_start_date=dates(horizon)[0], grid_step_days=7)
    assert iter(starts) is starts
    assert tuple(starts) == dates(*expected)


def test_inclusive_grid_at_date_limit_does_not_advance_past_equal_bounds():
    assert _build_date_grid(start_date=date.max, end_date=date.max, step_days=7) == (date.max,)


def test_diagnostics_keeps_lazy_rate_evaluation_before_date_overflow():
    curve = RecordingCurve()
    curve.reference_date = date.max - timedelta(days=1)
    with pytest.raises(OverflowError):
        build_forward_observations(curve=curve, last_supported_date=date.max,
                                   forward_period_days=1, grid_step_days=7)
    assert curve.forward_dates == [(curve.reference_date, date.max)]


def test_diagnostics_nonfinite_rate_stops_before_advancing():
    curve = RecordingCurve(float("nan"))
    with pytest.raises(ValueError, match="Curve produced non-finite forward rate"):
        build_forward_observations(curve=curve, last_supported_date=dates(18)[0],
                                   forward_period_days=3, grid_step_days=7)
    assert curve.forward_dates == [(REFERENCE, dates(3)[0])]


def test_locality_accepts_numpy_sensitivities_without_changing_return_types():
    import numpy as np

    result = calculate_forward_sensitivity_locality(
        reference_date=REFERENCE, shock_pillar_date=dates(360)[0],
        forward_start_dates=dates(0, 180), sensitivities_bp_per_bp=np.array([1.0, 1.0]),
    )
    assert type(result.weighted_center_years) is float
    assert type(result.center_offset_from_shock_years) is float
    assert result.center_offset_from_shock_years == -0.75
