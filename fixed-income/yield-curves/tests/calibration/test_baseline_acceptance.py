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
