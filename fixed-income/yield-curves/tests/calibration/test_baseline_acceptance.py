"""Operational input rejection and assessment of existing calibrations."""

from copy import copy, deepcopy
from dataclasses import replace
from datetime import date, datetime
from math import isfinite, nextafter
from types import SimpleNamespace
from unittest.mock import Mock

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
    (invalid_second(trade_date=datetime(2026, 9, 15)), "INVALID_QUOTE_DATE:3M"),
    (invalid_second(contractual_maturity_date=datetime(2026, 12, 17)), "INVALID_QUOTE_DATE:3M"),
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


@pytest.mark.parametrize("case", ["empty_checks", "pass_checks_with_issue"])
def test_valid_structure_still_requires_checks_and_no_issues(result, monkeypatch, case):
    prepared = prepare_baseline_inputs(quotes=QUOTES, calendar=CALENDAR)
    checks = () if case == "empty_checks" else result.acceptance.checks
    issues = () if case == "empty_checks" else ("CONTROLLED_ISSUE",)
    reprice = Mock(return_value=(checks, issues))
    monkeypatch.setattr(baseline, "_independently_reprice", reprice)

    acceptance = baseline._assess_prepared_calibration(
        calibration_result=result.calibration_result,
        quotes=prepared.quotes, calendar=prepared.calendar.to_calendar(),
        prepared=prepared, input_issues=(),
        acceptance_policy=baseline.STANDARD_ACCEPTANCE_POLICY,
    )

    reprice.assert_called_once_with(
        calibration_result=result.calibration_result,
        quotes=prepared.quotes, calendar=prepared.calendar.to_calendar(),
        pass_tolerance_bp=baseline.STANDARD_ACCEPTANCE_POLICY.pass_tolerance_bp,
        fail_tolerance_bp=baseline.STANDARD_ACCEPTANCE_POLICY.fail_tolerance_bp,
    )
    assert acceptance.calibration_success is True
    assert acceptance.structural_valid is True
    assert acceptance.checks == checks
    assert acceptance.issues == issues
    assert acceptance.accepted_for_use is False
    if case == "empty_checks":
        assert acceptance.checks == ()
        assert acceptance.issues == ()
        assert acceptance.max_abs_repricing_error_bp == float("inf")
    else:
        assert acceptance.checks
        assert all(c.status is repricing.InstrumentValidationStatus.PASS
                   for c in acceptance.checks)
        assert isfinite(acceptance.max_abs_repricing_error_bp)
        assert acceptance.issues == ("CONTROLLED_ISSUE",)


@pytest.mark.parametrize("error", [
    ValueError("Curve cannot price requested date"),
    ZeroDivisionError("Controlled pricing arithmetic failure"),
], ids=["value_error", "arithmetic_error"])
def test_pricing_domain_error_becomes_rejection(result, monkeypatch, error):
    fail = Mock(side_effect=error)
    monkeypatch.setattr(repricing, "calculate_par_rate", fail)
    acceptance = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR
    )
    fail.assert_called_once()
    assert acceptance.calibration_success is True
    assert acceptance.structural_valid is True
    assert acceptance.accepted_for_use is False
    assert acceptance.issues == ("REPRICING_FAILED",)
    assert acceptance.max_abs_repricing_error_bp == float("inf")
    assert acceptance.checks == ()


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


@pytest.mark.parametrize("field", [
    "success", "message", "function_evaluations", "jacobian_evaluations",
    "cost", "optimality", "max_abs_repricing_error_bp", "rmse_repricing_error_bp",
    "checks[0].tenor", "checks[0].market_quote", "checks[0].model_quote",
    "checks[0].error_bp",
])
def test_mutating_calibration_after_build_invalidates_live_result(result, field):
    changed = deepcopy(result)
    assert result.accepted_for_use is True
    assert changed.accepted_for_use is True
    assert changed.acceptance.is_bound_to(changed.calibration_result, changed.financial_context)

    target = changed.calibration_result
    original = result.calibration_result
    if field.startswith("checks[0]."):
        target = target.checks[0]
        original = original.checks[0]
        field = field.split(".", 1)[1]
    old_value = getattr(target, field)
    if field == "success":
        new_value = False
    elif field in ("message", "tenor"):
        new_value = old_value + "_CONTROLLED_MUTATION"
    elif field in ("function_evaluations", "jacobian_evaluations"):
        new_value = 1 if old_value is None else old_value + 1
    else:
        assert isfinite(old_value)
        new_value = nextafter(old_value, float("inf"))
        assert new_value.hex() != float(old_value).hex()
    assert new_value != old_value
    # Bypass frozen fields only on the copied payload, one retained value per case.
    object.__setattr__(target, field, new_value)

    assert changed.accepted_for_use is False
    assert changed.acceptance.is_bound_to(
        changed.calibration_result, changed.financial_context,
    ) is False
    assert changed.acceptance.accepted_for_use is True
    assert getattr(original, field) == old_value
    assert result.accepted_for_use is True


@pytest.mark.parametrize("state,historical_accepted,bound,expected", [
    ("accepted_bound", True, True, True),
    ("rejected_bound", False, True, False),
    ("accepted_stale", True, False, False),
], ids=["accepted_bound", "rejected_bound", "accepted_stale"])
def test_live_acceptance_query_does_no_financial_work(
    result, monkeypatch, state, historical_accepted, bound, expected,
):
    from yield_curves import bootstrap, calibration, inputs, pricing

    # Finish financial setup before installing any sentinels.
    candidate = result
    if state == "rejected_bound":
        failed = replace(result.calibration_result, success=False)
        prepared = result.financial_context.inputs
        assessed = baseline._assess_prepared_calibration(
            calibration_result=failed,
            quotes=prepared.quotes, calendar=prepared.calendar.to_calendar(),
            prepared=prepared, input_issues=(),
            acceptance_policy=result.acceptance.acceptance_policy,
            financial_context=result.financial_context,
        )
        assert assessed.issues == ("CALIBRATION_SOLVER_FAILED",)
        candidate = baseline.BaselineResult(failed, assessed, result.financial_context)
    elif state == "accepted_stale":
        candidate = deepcopy(result)
        object.__setattr__(candidate.calibration_result, "message",
                           candidate.calibration_result.message + "_STALE")

    assert candidate.acceptance.accepted_for_use is historical_accepted
    assert candidate.acceptance.is_bound_to(
        candidate.calibration_result, candidate.financial_context,
    ) is bound
    historical_assessment = candidate.acceptance
    historical_binding = historical_assessment.binding
    assessment_before = deepcopy(historical_assessment)
    calibration_before = candidate.calibration_result
    context_before = candidate.financial_context
    payload_before = baseline.BaselinePayloadBinding.capture(
        calibration_before, historical_binding.evaluation_inputs,
        context_before, historical_assessment.acceptance_policy,
    )

    # Patch the defining modules and the aliases actually imported by each caller.
    boundaries = (
        (baseline, ("prepare_baseline_inputs", "_independently_reprice",
                    "reprice_calibration_instruments", "assess_baseline_calibration",
                    "_assess_prepared_calibration", "build_baseline_ftiie_curve",
                    "calibrate_ftiie_ois_curve_simultaneously")),
        (inputs, ("prepare_baseline_inputs",)),
        (repricing, ("reprice_calibration_instruments", "calculate_par_rate")),
        (pricing, ("calculate_par_rate", "value_ftiie_ois")),
        (calibration, ("calibrate_ftiie_ois_curve_simultaneously",
                       "bootstrap_ftiie_ois_curve", "least_squares", "calculate_par_rate")),
        (bootstrap, ("bootstrap_ftiie_ois_curve", "bootstrap_ftiie_ois_curve_with_method",
                     "brentq", "calculate_par_rate", "value_ftiie_ois")),
    )
    sentinels = []
    with monkeypatch.context() as blocked:
        for module, names in boundaries:
            for name in names:
                location = f"{module.__name__}.{name}"
                sentinel = Mock(name=location, side_effect=AssertionError(location))
                blocked.setattr(module, name, sentinel)
                sentinels.append(sentinel)
        value_1 = candidate.accepted_for_use
        value_2 = candidate.accepted_for_use
        assert value_1 is expected
        assert value_2 is expected
        for sentinel in sentinels:
            sentinel.assert_not_called()

    assert candidate.acceptance is historical_assessment
    assert candidate.acceptance == assessment_before
    assert candidate.acceptance.binding is historical_binding
    assert candidate.acceptance.binding == assessment_before.binding
    assert candidate.calibration_result is calibration_before
    assert candidate.financial_context is context_before
    assert baseline.BaselinePayloadBinding.capture(
        candidate.calibration_result, historical_binding.evaluation_inputs,
        candidate.financial_context, candidate.acceptance.acceptance_policy,
    ) == payload_before
    assert candidate.acceptance.accepted_for_use is historical_accepted
    assert candidate.acceptance.is_bound_to(
        candidate.calibration_result, candidate.financial_context,
    ) is bound


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


@pytest.mark.parametrize("success", [True, False])
def test_builder_always_captures_standard_acceptance(result, monkeypatch, success):
    from types import MappingProxyType
    from yield_curves import engine_capabilities

    capabilities = engine_capabilities.METHOD_CAPABILITIES
    reordered = MappingProxyType(dict(reversed(tuple(capabilities.items()))))
    assert reordered == capabilities
    assert tuple(reordered) != tuple(capabilities)
    monkeypatch.setattr(engine_capabilities, "METHOD_CAPABILITIES", reordered)
    initial_dfs = list(result.curve.discount_factors)
    calls = []

    def solve(*, quotes, calendar, interpolation_method, initial_discount_factors):
        calls.append(interpolation_method)
        assert interpolation_method is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
        assert quotes == QUOTES
        assert calendar == CALENDAR
        assert initial_discount_factors == tuple(initial_dfs)
        return replace(result.calibration_result, success=success)

    monkeypatch.setattr(
        baseline, "calibrate_ftiie_ois_curve_simultaneously", solve,
    )
    built = baseline.build_baseline_ftiie_curve(
        quotes=QUOTES, calendar=CALENDAR, initial_discount_factors=initial_dfs,
    )
    assert calls == [CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO]
    assert built.financial_context.policy.interpolation_method is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
    policy = built.acceptance.acceptance_policy
    assert built.acceptance.is_standard_acceptance
    assert policy == baseline.STANDARD_ACCEPTANCE_POLICY
    assert built.financial_context.policy == result.financial_context.policy
    assert policy.kind is baseline.AcceptanceKind.STANDARD_BASELINE_ACCEPTANCE
    assert policy.identifier == "FTIIE_STANDARD_BASELINE_ACCEPTANCE_V1"
    assert policy.pass_tolerance_bp == built.acceptance.pass_tolerance_bp == 0.01
    assert policy.fail_tolerance_bp == built.acceptance.fail_tolerance_bp == 0.10
    assert built.financial_context.policy.acceptance_policy == policy
    assert built.financial_context.policy.baseline_identifier == "FTIIE_CUBIC_SIMULTANEOUS_V1"
    assert built.acceptance.binding.acceptance_policy == policy
    assert built.acceptance.is_bound_to(built.calibration_result, built.financial_context)
    assert built.accepted_for_use is success


@pytest.mark.parametrize("tolerances,expected", [
    ({}, (0.01, 0.10)),
    ({"pass_tolerance_bp": 0.01, "fail_tolerance_bp": 0.10}, (0.01, 0.10)),
    ({"pass_tolerance_bp": 0.001, "fail_tolerance_bp": 0.01}, (0.001, 0.01)),
    ({"pass_tolerance_bp": 1.0, "fail_tolerance_bp": 2.0}, (1.0, 2.0)),
    ({"pass_tolerance_bp": 0.01}, (0.01, 0.10)),
    ({"fail_tolerance_bp": 0.10}, (0.01, 0.10)),
])
def test_standalone_identity_depends_on_explicit_path(result, tolerances, expected):
    assessed = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR,
        **tolerances,
    )
    assert assessed.accepted_for_use
    assert all(c.status is repricing.InstrumentValidationStatus.PASS for c in assessed.checks)
    policy = assessed.acceptance_policy
    assert (assessed.pass_tolerance_bp, assessed.fail_tolerance_bp) == expected
    assert (policy.pass_tolerance_bp, policy.fail_tolerance_bp) == expected
    assert assessed.is_standard_acceptance is (not tolerances)
    if tolerances:
        assert policy.kind is baseline.AcceptanceKind.CUSTOM_ANALYTICAL_ASSESSMENT
        assert policy.identifier is None
    else:
        assert policy == baseline.STANDARD_ACCEPTANCE_POLICY
    assert assessed.binding.acceptance_policy == policy
    assert assessed.is_bound_to(result.calibration_result)
    assert assessed.binding.financial_context is None
    # A PASS (standard or custom) cannot be attached to a captured build context.
    with pytest.raises(ValueError, match="binding mismatch"):
        replace(result, acceptance=assessed)


def test_custom_cannot_be_relabelled_standard_without_invalidating_binding(result):
    custom = baseline.assess_baseline_calibration(
        calibration_result=result.calibration_result, quotes=QUOTES, calendar=CALENDAR,
        pass_tolerance_bp=0.01, fail_tolerance_bp=0.10,
    )
    relabelled = replace(custom, acceptance_policy=baseline.STANDARD_ACCEPTANCE_POLICY)
    assert not relabelled.is_bound_to(result.calibration_result)
    with pytest.raises(ValueError, match="binding mismatch"):
        baseline.BaselineResult(result.calibration_result, relabelled)


@pytest.mark.parametrize("changes", [
    {"acceptance_policy": None},
    {"pass_tolerance_bp": 0.001},
    {"fail_tolerance_bp": 0.01},
])
def test_acceptance_identity_and_effective_tolerances_are_bound(result, changes):
    with pytest.raises(ValueError, match="binding mismatch"):
        replace(result, acceptance=replace(result.acceptance, **changes))


@pytest.mark.parametrize("error_bp,status", [
    (0.0, "PASS"), (0.01, "PASS"), (0.010000001, "REVIEW"),
    (0.10, "REVIEW"), (0.100000001, "FAIL"), (float("inf"), "FAIL"),
])
def test_standard_threshold_boundaries_preserve_baseline_acceptance(
    result, monkeypatch, error_bp, status,
):
    # Inject controlled errors at the pricing boundary; retain real classification
    # and baseline acceptance logic without floating point subtraction at endpoints.
    def reprice(**kwargs):
        assert kwargs["pass_tolerance_bp"] == 0.01
        assert kwargs["fail_tolerance_bp"] == 0.10
        checks = []
        for check in result.acceptance.checks:
            classified = repricing.classify_repricing_error(
                absolute_error_bp=error_bp,
                pass_tolerance_bp=kwargs["pass_tolerance_bp"],
                fail_tolerance_bp=kwargs["fail_tolerance_bp"],
            )
            assert classified.value == status
            checks.append(replace(check, error_bp=error_bp,
                                  absolute_error_bp=error_bp, status=classified))
        return tuple(checks)

    monkeypatch.setattr(baseline, "reprice_calibration_instruments", reprice)
    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously",
                        lambda **kwargs: result.calibration_result)
    built = baseline.build_baseline_ftiie_curve(quotes=QUOTES, calendar=CALENDAR)
    assert built.acceptance.is_standard_acceptance
    assert built.accepted_for_use is (status == "PASS")
