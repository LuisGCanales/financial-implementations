"""Operational input rejection and assessment of existing calibrations."""

from copy import copy
from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from yield_curves import baseline, repricing
from yield_curves.calendars import BusinessCalendar, CalendarCoverageError
from yield_curves.curves import CurveInterpolationMethod, LogLinearDiscountCurve
from yield_curves.inputs import BaselineInputError, prepare_baseline_inputs
from yield_curves.quotes import OISQuote


QUOTES = (
    OISQuote("1M", date(2026, 9, 15), date(2026, 10, 19), 0.05),
    OISQuote("3M", date(2026, 9, 15), date(2026, 12, 17), 0.051),
)
CALENDAR = BusinessCalendar(
    "TEST", coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31)
)


@pytest.fixture(scope="module")
def result():
    result = baseline.build_baseline_ftiie_curve(quotes=QUOTES, calendar=CALENDAR)
    assert result.accepted_for_use
    return result


def invalid_second(**changes):
    fields = dict(tenor="3M", trade_date=date(2026, 9, 15),
                  contractual_maturity_date=date(2026, 12, 17), par_rate=0.051)
    fields.update(changes)
    return (QUOTES[0], SimpleNamespace(**fields))


INVALID_INPUTS = [
    ((), "EMPTY_QUOTE_SET"),
    (QUOTES[:1], "INSUFFICIENT_QUOTES_FOR_CUBIC"),
    (invalid_second(tenor=""), "INVALID_TENOR:quote[1]"),
    (invalid_second(tenor="1M"), "DUPLICATE_TENOR:1M"),
    (invalid_second(trade_date=date(2026, 9, 14)), "MULTIPLE_TRADE_DATES"),
    (invalid_second(trade_date="2026-09-15"), "INVALID_QUOTE_DATE:3M"),
    (invalid_second(contractual_maturity_date=date(2026, 9, 15)), "INVALID_MATURITY:3M"),
    (invalid_second(contractual_maturity_date=QUOTES[0].contractual_maturity_date), "DUPLICATE_MATURITY:3M"),
    (QUOTES[::-1], "NON_INCREASING_MATURITY:1M"),
    (invalid_second(par_rate=float("nan")), "NON_FINITE_OR_INVALID_QUOTE:3M"),
    (invalid_second(par_rate=float("inf")), "NON_FINITE_OR_INVALID_QUOTE:3M"),
    (invalid_second(par_rate="0.05"), "NON_FINITE_OR_INVALID_QUOTE:3M"),
    (invalid_second(par_rate=True), "NON_FINITE_OR_INVALID_QUOTE:3M"),
    ((replace(QUOTES[0], contractual_maturity_date=date(2026, 10, 17)),
      replace(QUOTES[1], contractual_maturity_date=date(2026, 10, 18))),
     "NON_INCREASING_PILLAR:3M"),
    ((replace(QUOTES[0], contractual_maturity_date=date(2026, 9, 16)), QUOTES[1]),
     "INVALID_INSTRUMENT:1M"),
]


@pytest.mark.parametrize("quotes,code", INVALID_INPUTS)
def test_bad_inputs_never_reach_solver(quotes, code, monkeypatch):
    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously",
                        lambda **kwargs: pytest.fail("Unexpected solver call"))
    with pytest.raises(BaselineInputError) as error:
        baseline.build_baseline_ftiie_curve(quotes=quotes, calendar=CALENDAR)
    assert code in error.value.issues


@pytest.mark.parametrize("quotes,code", INVALID_INPUTS)
def test_assessment_rejects_bad_inputs_without_repricing(result, quotes, code, monkeypatch):
    monkeypatch.setattr(baseline, "_independently_reprice",
                        lambda **kwargs: pytest.fail("Unexpected repricing"))
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=quotes, calendar=CALENDAR
    )
    assert acceptance.calibration_success
    assert not acceptance.accepted_for_use
    assert not acceptance.structural_valid
    assert acceptance.checks == ()
    assert code in acceptance.issues


@pytest.mark.parametrize("calendar,code", [
    (BusinessCalendar("UNKNOWN"), "CALENDAR_COVERAGE_UNSPECIFIED"),
    (replace(CALENDAR, coverage_end=date(2026, 10, 19)), "CALENDAR_COVERAGE_INSUFFICIENT"),
    (replace(CALENDAR, coverage_end=date(2026, 12, 17)), "CALENDAR_COVERAGE_INSUFFICIENT"),
])
def test_calendar_rejection_during_build_and_assessment(result, calendar, code, monkeypatch):
    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously",
                        lambda **kwargs: pytest.fail("Unexpected solver call"))
    with pytest.raises(CalendarCoverageError):
        baseline.build_baseline_ftiie_curve(quotes=QUOTES, calendar=calendar)
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=calendar
    )
    assert code in acceptance.issues
    assert not acceptance.accepted_for_use
    assert acceptance.checks == ()


@pytest.mark.parametrize("field,value,code", [
    ("node_dates", (), "NODE_COUNT_MISMATCH"),
    ("discount_factors", (), "DISCOUNT_FACTOR_COUNT_MISMATCH"),
    ("discount_factors", (float("nan"), 0.98), "INVALID_DISCOUNT_FACTORS"),
    ("discount_factors", (0.0, 0.98), "INVALID_DISCOUNT_FACTORS"),
    ("node_dates", (date(2026, 12, 21), date(2026, 10, 21)), "NODE_DATES_NOT_STRICTLY_INCREASING"),
    ("reference_date", date(2026, 9, 18), "CURVE_REFERENCE_DATE_MISMATCH"),
    ("node_dates", (date(2026, 10, 22), date(2026, 12, 22)), "CURVE_PILLAR_DATES_MISMATCH"),
])
def test_corrupt_structure_is_rejected_before_pricing(result, monkeypatch, field, value, code):
    # Bypass constructor invariants solely to simulate a corrupt supplied result.
    curve = copy(result.curve)
    object.__setattr__(curve, field, value)
    monkeypatch.setattr(baseline, "_independently_reprice",
                        lambda **kwargs: pytest.fail("Unexpected repricing"))
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=replace(result.calibration_result, curve=curve),
        quotes=QUOTES, calendar=CALENDAR,
    )
    assert code in acceptance.issues
    assert not acceptance.structural_valid
    assert not acceptance.accepted_for_use
    assert acceptance.checks == ()


def test_curve_type_cannot_be_disguised_by_method_metadata(result):
    curve = LogLinearDiscountCurve(result.curve.reference_date,
                                   result.curve.node_dates, result.curve.discount_factors)
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=replace(result.calibration_result, curve=curve),
        quotes=QUOTES, calendar=CALENDAR,
    )
    assert "BASELINE_CURVE_TYPE_MISMATCH" in acceptance.issues
    assert not acceptance.accepted_for_use


@pytest.mark.parametrize("change,code", [
    ("failed", "CALIBRATION_SOLVER_FAILED"),
    ("method", "BASELINE_INTERPOLATION_METHOD_MISMATCH"),
    ("count", "CALIBRATION_CHECK_COUNT_MISMATCH"),
    ("tenor", "CALIBRATION_CHECK_TENOR_MISMATCH"),
])
def test_metadata_and_solver_rejection(result, change, code):
    calibration = result.calibration_result
    changes = {
        "failed": {"success": False},
        "method": {"interpolation_method": CurveInterpolationMethod.LOG_LINEAR_DF},
        "count": {"checks": ()},
        "tenor": {"checks": tuple(reversed(calibration.checks))},
    }
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=replace(calibration, **changes[change]), quotes=QUOTES, calendar=CALENDAR
    )
    assert code in acceptance.issues
    assert not acceptance.accepted_for_use


@pytest.mark.parametrize("pass_bp,fail_bp", [(float("inf"), float("inf")),
                                           (float("nan"), 0.1), (0.01, float("nan")),
                                           (-0.01, 0.1), (0.1, 0.1)])
def test_invalid_acceptance_configuration_raises(result, pass_bp, fail_bp):
    with pytest.raises(ValueError, match="tolerances"):
        baseline.assess_baseline_calibration(
            calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR,
            pass_tolerance_bp=pass_bp, fail_tolerance_bp=fail_bp,
        )


def test_pricing_domain_error_becomes_rejection(result, monkeypatch):
    def fail(**kwargs):
        raise ValueError("Curve cannot price requested date")
    monkeypatch.setattr(repricing, "calculate_par_rate", fail)
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR
    )
    assert not acceptance.accepted_for_use
    assert acceptance.issues == ("REPRICING_FAILED",)
    assert acceptance.max_abs_repricing_error_bp == float("inf")


@pytest.mark.parametrize("rate", [0.0, -0.01])
def test_zero_and_negative_quotes_pass_input_preparation(rate):
    quotes = tuple(replace(quote, par_rate=rate) for quote in QUOTES)
    prepared = prepare_baseline_inputs(quotes=quotes, calendar=CALENDAR)
    assert prepared.quotes == quotes
    assert prepared.reference_date == date(2026, 9, 17)


def test_build_freezes_external_inputs_before_solver(monkeypatch):
    from dataclasses import FrozenInstanceError

    external = [SimpleNamespace(**{name: getattr(q, name) for name in
                ('tenor', 'trade_date', 'contractual_maturity_date', 'par_rate')})
                for q in QUOTES]
    holidays, weekends = set(), {5, 6}
    calendar = replace(CALENDAR, holidays=holidays, weekend_days=weekends)
    solve = baseline.calibrate_ftiie_ois_curve_simultaneously

    def mutate_callers_and_solve(**kwargs):
        external[0].par_rate = 0.9
        external[0].trade_date = date(2025, 1, 1)
        external.reverse()
        holidays.add(date(2026, 9, 17))
        weekends.add(4)
        assert kwargs['quotes'] == QUOTES
        assert kwargs['calendar'].holidays == frozenset()
        assert kwargs['calendar'].weekend_days == frozenset({5, 6})
        return solve(**kwargs)

    monkeypatch.setattr(baseline, 'calibrate_ftiie_ois_curve_simultaneously',
                        mutate_callers_and_solve)
    built = baseline.build_baseline_ftiie_curve(quotes=external, calendar=calendar)
    context, binding = built.financial_context, built.acceptance.binding
    external[0].contractual_maturity_date = date(2026, 11, 1)
    holidays.clear()
    weekends.clear()
    assert built.accepted_for_use
    assert context.inputs.quotes == QUOTES
    assert context.inputs.calendar.holidays == ()
    assert context.inputs.calendar.weekend_days == (5, 6)
    assert built.acceptance.binding == binding
    with pytest.raises(FrozenInstanceError):
        context.inputs.quotes[0].par_rate = 0.8


@pytest.mark.parametrize('field,value', [
    ('trade_date', date(2026, 9, 14)),
    ('contractual_maturity_date', date(2026, 10, 20)),
])
def test_financial_context_distinguishes_quote_dates(result, field, value):
    quotes = tuple(replace(q, **{field: value}) if field == 'trade_date' or i == 0 else q
                   for i, q in enumerate(QUOTES))
    other = baseline.build_baseline_ftiie_curve(quotes=quotes, calendar=CALENDAR)
    assert other.accepted_for_use
    assert [q.tenor for q in quotes] == [q.tenor for q in QUOTES]
    assert [q.par_rate for q in quotes] == [q.par_rate for q in QUOTES]
    assert result.financial_context != other.financial_context
    assert result.acceptance.binding != other.acceptance.binding


def test_policy_is_captured_and_not_reconstructed_from_later_constants(result, monkeypatch):
    policy = result.financial_context.policy
    assert policy.baseline_identifier == baseline.BASELINE_IDENTIFIER
    assert policy.calibration_approach == 'simultaneous_nodal_calibration'
    assert policy.interpolation_method is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
    assert policy.profile == 'Core-v1'
    assert policy.instrument == 'FTIIE_OIS'
    assert policy.conventions.floating_index_tenor_days == 1
    assert policy.conventions.calendar_id == 'MXMC'
    assert policy.conventions.calibration_notional == 1
    assert policy.conventions.floating_spread == 0
    assert policy.conventions.day_count == 'ACT_360'
    assert policy.projection_discounting == 'same_curve'
    assert policy.reference_date_rule == 'common_effective_date'
    assert policy.pillar_date_rule == 'final_payment_date'
    assert policy.spline_boundary == 'natural'
    assert policy.zero_at_origin == 'first_nodal_zero'
    assert policy.extrapolation is False
    assert result.financial_context.inputs.calendar.name == 'TEST'
    monkeypatch.setattr(baseline, 'BASELINE_IDENTIFIER', 'future policy')
    assert result.financial_context.policy == policy
    assert result.accepted_for_use


@pytest.mark.parametrize('change', ['df', 'reference', 'nodes', 'method', 'success', 'checks'])
def test_replacing_financial_payload_rejects_old_acceptance(result, change):
    from math import nextafter

    calibration = result.calibration_result
    curve = copy(result.curve)
    if change == 'df':
        # One representable step is enough, even far below acceptance tolerances.
        object.__setattr__(curve, 'discount_factors',
                           (nextafter(curve.discount_factors[0], 1.0), curve.discount_factors[1]))
    elif change == 'reference':
        object.__setattr__(curve, 'reference_date', date(2026, 9, 18))
    elif change == 'nodes':
        object.__setattr__(curve, 'node_dates', tuple(reversed(curve.node_dates)))
    changes = {'curve': curve}
    if change == 'method':
        changes['interpolation_method'] = CurveInterpolationMethod.LOG_LINEAR_DF
    elif change == 'success':
        changes['success'] = False
    elif change == 'checks':
        changes['checks'] = tuple(reversed(calibration.checks))
    altered = replace(calibration, **changes)
    assert not result.acceptance.is_bound_to(altered, result.financial_context)
    with pytest.raises(ValueError, match='binding mismatch'):
        replace(result, calibration_result=altered)


@pytest.mark.parametrize('part', ['c', 'x', 'extrapolate'])
def test_mutable_spline_state_invalidates_live_result(result, part):
    from copy import deepcopy

    changed = deepcopy(result)
    spline = changed.curve._spline_object
    if part == 'extrapolate':
        spline.extrapolate = True
    else:
        getattr(spline, part).flat[0] += 0.001
    assert not changed.accepted_for_use
    assert not changed.acceptance.is_bound_to(changed.calibration_result, changed.financial_context)
    assert result.accepted_for_use


def test_swapping_acceptance_or_context_is_detected(result):
    other = baseline.build_baseline_ftiie_curve(
        quotes=tuple(replace(q, par_rate=q.par_rate + 0.001) for q in QUOTES),
        calendar=CALENDAR,
    )
    with pytest.raises(ValueError, match='binding mismatch'):
        replace(result, acceptance=other.acceptance)
    with pytest.raises(ValueError, match='binding mismatch'):
        replace(result, financial_context=other.financial_context)
    # Equal financial values remain compatible, independent of Python identity.
    assert replace(result, calibration_result=replace(result.calibration_result)).accepted_for_use


def test_standalone_assessment_binds_evaluation_without_inventing_build_history(result):
    assessed = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR,
    )
    assert assessed.accepted_for_use
    assert assessed.binding.financial_context is None
    assert assessed.binding.evaluation_inputs == result.financial_context.inputs
    standalone = baseline.BaselineResult(result.calibration_result, assessed)
    assert standalone.financial_context is None
    assert standalone.accepted_for_use
    with pytest.raises(ValueError, match='binding mismatch'):
        replace(standalone, financial_context=result.financial_context)


def test_absent_curve_and_nonfinite_diagnostics_have_explicit_rejected_binding(result):
    calibration = replace(result.calibration_result, curve=None, cost=float('nan'))
    assessed = baseline.assess_baseline_calibration(
        calibration_result=calibration, quotes=QUOTES, calendar=CALENDAR,
    )
    assert not assessed.accepted_for_use
    assert assessed.is_bound_to(calibration)
    assert assessed.binding.reference_date is None
    assert assessed.binding.discount_factors == ()


def test_mutating_calibration_after_build_invalidates_live_result(result):
    from copy import deepcopy

    changed = deepcopy(result)
    object.__setattr__(changed.calibration_result, 'success', False)
    assert not changed.accepted_for_use
    assert result.accepted_for_use


def test_initial_vector_is_copied_before_preparation(result, monkeypatch):
    initial = list(result.curve.discount_factors)
    expected = tuple(initial)
    prepare = baseline.prepare_baseline_inputs
    solve = baseline.calibrate_ftiie_ois_curve_simultaneously

    def mutate_during_preparation(**kwargs):
        initial[:] = [0.5, 0.4]
        return prepare(**kwargs)

    def check_solver_inputs(**kwargs):
        assert kwargs['initial_discount_factors'] == expected
        return solve(**kwargs)

    monkeypatch.setattr(baseline, 'prepare_baseline_inputs', mutate_during_preparation)
    monkeypatch.setattr(baseline, 'calibrate_ftiie_ois_curve_simultaneously', check_solver_inputs)
    assert baseline.build_baseline_ftiie_curve(
        quotes=QUOTES, calendar=CALENDAR, initial_discount_factors=initial,
    ).accepted_for_use
