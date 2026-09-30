"""Shared contracts, compatibility imports and caller-specific acceptance."""

from dataclasses import replace
from datetime import date

import pytest

from yield_curves import bootstrap, repricing
from yield_curves.research import validation
from yield_curves.baseline import (
    assess_baseline_calibration,
    build_baseline_ftiie_curve,
)
from yield_curves.calendars import BusinessCalendar
from yield_curves.curves import FlatContinuousZeroCurve
from yield_curves.quotes import OISCalibrationQuote, OISQuote


TRADE_DATE = date(2026, 9, 15)


def test_historical_imports_preserve_type_and_function_identity():
    assert bootstrap.OISCalibrationQuote is OISCalibrationQuote
    assert validation.InstrumentRepricingCheck is repricing.InstrumentRepricingCheck
    assert validation.InstrumentValidationStatus is repricing.InstrumentValidationStatus
    assert validation.classify_repricing_error is repricing.classify_repricing_error


@pytest.mark.parametrize("rate", [-0.01, 0.0, 0.08])
def test_general_quote_supports_finite_rates(rate):
    quote = OISQuote("1M", TRADE_DATE, date(2026, 10, 19), rate)
    assert quote.par_rate == rate


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), -float("inf")])
def test_general_quote_rejects_nonfinite_rates(rate):
    with pytest.raises(ValueError, match="must be finite"):
        OISQuote("1M", TRADE_DATE, date(2026, 10, 19), rate)


@pytest.mark.parametrize(
    "error,status",
    [(0.0, "PASS"), (0.01, "PASS"), (0.05, "REVIEW"),
     (0.10, "REVIEW"), (0.1001, "FAIL"), (float("nan"), "FAIL"),
     (float("inf"), "FAIL")],
)
def test_shared_classifier_preserves_boundaries(error, status):
    assert repricing.classify_repricing_error(
        absolute_error_bp=error, pass_tolerance_bp=0.01, fail_tolerance_bp=0.10
    ).value == status


@pytest.mark.parametrize("pass_bp,fail_bp", [(-0.01, 0.10), (0.1, 0.1), (0.1, 0.01)])
def test_shared_classifier_rejects_invalid_tolerances(pass_bp, fail_bp):
    with pytest.raises(ValueError):
        repricing.classify_repricing_error(
            absolute_error_bp=0.0,
            pass_tolerance_bp=pass_bp,
            fail_tolerance_bp=fail_bp,
        )


def test_curve_only_repricing_has_expected_sign_order_and_custom_tolerances():
    # A zero-rate curve implies zero par rates regardless of the supplied coupon.
    quotes = (
        OISQuote("1M", TRADE_DATE, date(2026, 10, 19), 0.0),
        OISQuote("3M", TRADE_DATE, date(2026, 12, 17), 0.000005),
    )
    checks = repricing.reprice_calibration_instruments(
        curve=FlatContinuousZeroCurve(date(2026, 9, 17), 0.0),
        quotes=quotes,
        calendar=BusinessCalendar("WEEKENDS_ONLY"),
        pass_tolerance_bp=0.06,
        fail_tolerance_bp=0.10,
    )
    assert [check.tenor for check in checks] == ["1M", "3M"]
    assert [check.model_quote for check in checks] == pytest.approx([0.0, 0.0])
    assert [check.error_bp for check in checks] == pytest.approx([0.0, -0.05])
    assert all(check.status.value == "PASS" for check in checks)


@pytest.fixture(scope="module")
def calibrated_general_quotes():
    quotes = (
        OISQuote("1M", TRADE_DATE, date(2026, 10, 19), 0.05),
        OISQuote("3M", TRADE_DATE, date(2026, 12, 17), 0.05),
    )
    calendar = BusinessCalendar(
        "WEEKENDS_ONLY", coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31)
    )
    sequential = bootstrap.bootstrap_ftiie_ois_curve(quotes=quotes, calendar=calendar)
    baseline = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)
    assert baseline.accepted_for_use
    return quotes, calendar, sequential, baseline


@pytest.mark.parametrize(
    "bump_bp, instrument_status, curve_status, accepted",
    [(0.0, "PASS", "VALID", True), (0.05, "REVIEW", "REVIEW", False),
     (0.20, "FAIL", "INVALID", False)],
)
def test_shared_repricing_keeps_distinct_acceptance_policies(
    calibrated_general_quotes, bump_bp, instrument_status, curve_status, accepted
):
    quotes, calendar, sequential, baseline = calibrated_general_quotes
    shocked = (quotes[0], replace(quotes[1], par_rate=quotes[1].par_rate + bump_bp / 10_000))
    # Deliberately retain the calibrated curves: this tests final-curve checks,
    # not how a new calibration fits a changed quote set.
    report = validation.validate_bootstrap_result(
        bootstrap_result=sequential, quotes=shocked, calendar=calendar
    )
    acceptance = assess_baseline_calibration(
        calibration_result=baseline.calibration_result,
        quotes=shocked,
        calendar=calendar,
    )
    assert report.status.value == curve_status
    assert report.instrument_checks[-1].status.value == instrument_status
    assert acceptance.checks[-1].status.value == instrument_status
    assert acceptance.accepted_for_use is accepted
    assert acceptance.calibration_success


@pytest.mark.parametrize("model_rate", [float("nan"), float("inf")])
def test_nonfinite_repricing_preserves_each_callers_issue_contract(
    calibrated_general_quotes, monkeypatch, model_rate
):
    quotes, calendar, sequential, baseline = calibrated_general_quotes
    monkeypatch.setattr(repricing, "calculate_par_rate", lambda **kwargs: model_rate)
    report = validation.validate_bootstrap_result(
        bootstrap_result=sequential, quotes=quotes, calendar=calendar
    )
    acceptance = assess_baseline_calibration(
        calibration_result=baseline.calibration_result, quotes=quotes, calendar=calendar
    )
    assert report.status.value == "INVALID"
    assert sum(issue.code == "REPRICING_FAIL" for issue in report.issues) == 2
    assert not acceptance.accepted_for_use
    assert "NON_FINITE_REPRICING_ERROR:1M" in acceptance.issues
    assert "NON_FINITE_REPRICING_ERROR:3M" in acceptance.issues
    assert "REPRICING_OUTSIDE_PASS_TOLERANCE" in acceptance.issues


def test_repricing_ignores_stored_calibration_quotes(calibrated_general_quotes):
    quotes, calendar, sequential, baseline = calibrated_general_quotes
    sequential = replace(
        sequential,
        steps=tuple(replace(step, model_quote=999.0) for step in sequential.steps),
    )
    calibration = replace(
        baseline.calibration_result,
        checks=tuple(replace(check, model_quote=999.0)
                     for check in baseline.calibration_result.checks),
    )
    checks = validation.independently_reprice_calibration_instruments(
        bootstrap_result=sequential, quotes=quotes, calendar=calendar
    )
    acceptance = assess_baseline_calibration(
        calibration_result=calibration, quotes=quotes, calendar=calendar
    )
    assert [check.model_quote for check in checks] == pytest.approx(
        [quote.par_rate for quote in quotes], abs=1e-9, rel=0
    )
    assert [check.model_quote for check in acceptance.checks] == pytest.approx(
        [quote.par_rate for quote in quotes], abs=1e-9, rel=0
    )
    assert acceptance.accepted_for_use


@pytest.mark.parametrize("holidays", [frozenset(), frozenset({date(2026, 9, 16), date(2026, 10, 19)})])
def test_four_paths_rebuild_identical_contracts(monkeypatch, holidays):
    from yield_curves import calibration, inputs, instruments
    from yield_curves.curves import CurveInterpolationMethod

    quotes = (
        OISQuote("1M", TRADE_DATE, date(2026, 10, 18), 0.05),
        OISQuote("3M", TRADE_DATE, date(2026, 12, 17), 0.051),
    )
    calendar = BusinessCalendar(
        "SUPPLIED", holidays=holidays,
        coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31),
    )
    # Preserve the pre-P02 construction as the contractual regression oracle.
    expected = tuple(instruments.build_ftiie_ois(
        trade_date=q.trade_date, maturity_date=q.contractual_maturity_date,
        fixed_rate=q.par_rate, notional=1.0, calendar=calendar,
    ) for q in quotes)
    captured = {}

    def capture(path):
        captured[path] = []
        def build(**kwargs):
            assert kwargs["calendar"] is calendar
            ois = instruments.build_calibration_ftiie_ois(**kwargs)
            captured[path].append(ois)
            return ois
        return build

    for module in (inputs, bootstrap, calibration, repricing):
        monkeypatch.setattr(module, "build_calibration_ftiie_ois", capture(module.__name__))

    prepared = inputs.prepare_baseline_inputs(quotes=quotes, calendar=calendar)
    sequential = bootstrap.bootstrap_ftiie_ois_curve(quotes=quotes, calendar=calendar)
    simultaneous = calibration.calibrate_ftiie_ois_curve_simultaneously(
        quotes=quotes, calendar=calendar,
        interpolation_method=CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
        initial_discount_factors=sequential.curve.discount_factors,
    )
    checks = repricing.reprice_calibration_instruments(
        curve=simultaneous.curve, quotes=quotes, calendar=calendar,
    )
    assert simultaneous.success
    assert all(check.status.value == "PASS" for check in checks)
    assert prepared.reference_date == date(2026, 9, 18 if holidays else 17)
    assert prepared.pillar_dates == (
        date(2026, 10, 22 if holidays else 21), date(2026, 12, 21),
    )
    for curve in (sequential.curve, simultaneous.curve):
        assert curve.reference_date == prepared.reference_date
        assert curve.node_dates == prepared.pillar_dates
    for built in captured.values():
        assert tuple(built) == expected  # Includes both legs and every observation.
    for index in range(len(quotes)):
        assert len({id(built[index]) for built in captured.values()}) == 4


def test_downstream_notional_does_not_change_calibration_contract():
    from yield_curves.instruments import build_calibration_ftiie_ois, build_ftiie_ois

    quote = OISQuote("1M", TRADE_DATE, date(2026, 10, 19), 0.05)
    calendar = BusinessCalendar("SUPPLIED")
    before = build_calibration_ftiie_ois(quote=quote, calendar=calendar)
    downstream = build_ftiie_ois(
        trade_date=quote.trade_date, maturity_date=quote.contractual_maturity_date,
        fixed_rate=quote.par_rate, calendar=calendar, notional=10_000_000,
    )
    after = build_calibration_ftiie_ois(quote=quote, calendar=calendar)
    assert before == after
    assert before is not after
    assert after.notional == 1.0
    assert after.floating_spread == 0.0
    assert all(c.notional == 1.0 for c in (*after.fixed_leg, *after.floating_leg))
    assert downstream.notional == 10_000_000


def test_forged_successful_solver_checks_cannot_make_bad_curve_pass(calibrated_general_quotes):
    quotes, calendar, _, baseline = calibrated_general_quotes
    calibration = baseline.calibration_result
    bad_curve = replace(calibration.curve, discount_factors=(0.99, 0.97))
    forged = replace(
        calibration, curve=bad_curve, success=True, cost=0.0, optimality=0.0,
        max_abs_repricing_error_bp=0.0, rmse_repricing_error_bp=0.0,
        checks=tuple(replace(check, model_quote=check.market_quote, error_bp=0.0)
                     for check in calibration.checks),
    )
    acceptance = assess_baseline_calibration(
        calibration_result=forged, quotes=quotes, calendar=calendar,
    )
    assert acceptance.structural_valid
    assert acceptance.calibration_success
    assert not acceptance.accepted_for_use
    assert any(check.status.value == "FAIL" for check in acceptance.checks)
    assert "REPRICING_OUTSIDE_PASS_TOLERANCE" in acceptance.issues
