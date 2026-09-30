from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from yield_curves.baseline import (
    BASELINE_IDENTIFIER,
    BASELINE_INTERPOLATION_METHOD,
    assess_baseline_calibration,
    build_baseline_ftiie_curve,
)
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.research.synthetic import (read_synthetic_ois_quotes_csv)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


@pytest.fixture(scope="module")
def quotes():
    return read_synthetic_ois_quotes_csv(QUOTES_PATH)


@pytest.fixture(scope="module")
def calendar():
    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture(scope="module")
def baseline_result(quotes, calendar):
    return build_baseline_ftiie_curve(
        quotes=quotes,
        calendar=calendar,
    )


def test_baseline_matches_pre_separation_reference(baseline_result, quotes, calendar):
    """Keep the numerical contract fixed while module boundaries change."""
    reference = json.loads(
        (PROJECT_ROOT / "tests/fixtures/ftiie_baseline_reference_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert reference["schema_version"] == 1
    assert BASELINE_IDENTIFIER == reference["baseline_identifier"]
    inputs = reference["inputs"]
    assert hashlib.sha256(QUOTES_PATH.read_bytes()).hexdigest() == inputs["quotes_sha256"]
    assert len(quotes) == inputs["quote_count"]
    holiday_bytes = "\n".join(
        sorted(day.isoformat() for day in calendar.holidays)
    ).encode("utf-8")
    assert calendar.name == inputs["calendar"]["name"]
    assert sorted(calendar.weekend_days) == inputs["calendar"]["weekend_days"]
    assert hashlib.sha256(holiday_bytes).hexdigest() == inputs["calendar"]["holidays_sha256"]

    curve = baseline_result.curve
    assert curve.reference_date.isoformat() == reference["reference_date"]
    assert (
        baseline_result.calibration_result.interpolation_method.value
        == reference["interpolation_method"]
    )
    acceptance = baseline_result.acceptance
    expected = reference["acceptance"]
    assert acceptance.calibration_success == expected["calibration_success"]
    assert acceptance.accepted_for_use == expected["accepted_for_use"]
    assert acceptance.structural_valid == expected["structural_valid"]
    assert list(acceptance.issues) == expected["issues"]
    assert acceptance.pass_tolerance_bp == expected["pass_tolerance_bp"]
    assert acceptance.max_abs_repricing_error_bp == pytest.approx(
        expected["max_abs_repricing_error_bp"], abs=1e-5, rel=0
    )

    assert len(curve.node_dates) == len(reference["nodes"])
    for day, df, node in zip(
        curve.node_dates, curve.discount_factors, reference["nodes"], strict=True
    ):
        assert day.isoformat() == node["date"]
        assert df == pytest.approx(node["discount_factor"], abs=1e-9, rel=0)
        assert curve.zero_rate(day) == pytest.approx(
            node["zero_rate"], abs=1e-9, rel=0
        )

    assert len(acceptance.checks) == len(expected["checks"])
    for check, saved in zip(acceptance.checks, expected["checks"], strict=True):
        assert check.tenor == saved["tenor"]
        assert check.market_quote == saved["market_quote"]
        assert check.status.value == saved["status"]
        assert check.model_quote == pytest.approx(
            saved["model_quote"], abs=1e-9, rel=0
        )
        assert check.error_bp == pytest.approx(saved["error_bp"], abs=1e-5, rel=0)
        assert check.absolute_error_bp == pytest.approx(
            saved["absolute_error_bp"], abs=1e-5, rel=0
        )

    assert len(reference["interior_observations"]) == len(curve.node_dates)
    for saved in reference["interior_observations"]:
        day = date.fromisoformat(saved["date"])
        end = date.fromisoformat(saved["forward_end_date"])
        assert curve.discount_factor(day) == pytest.approx(
            saved["discount_factor"], abs=1e-9, rel=0
        )
        assert curve.zero_rate(day) == pytest.approx(
            saved["zero_rate"], abs=1e-9, rel=0
        )
        assert curve.forward_rate(day, end) == pytest.approx(
            saved["forward_rate"], abs=1e-8, rel=0
        )


def test_baseline_uses_cubic_simultaneous_calibration(
    baseline_result,
) -> None:
    assert (
        baseline_result.calibration_result.interpolation_method
        is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
    )
    assert (
        BASELINE_INTERPOLATION_METHOD
        is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
    )


def test_baseline_is_accepted_for_synthetic_reference_quotes(
    baseline_result,
    quotes,
) -> None:
    assert baseline_result.calibration_result.success
    assert baseline_result.accepted_for_use
    assert baseline_result.acceptance.structural_valid
    assert len(baseline_result.curve.node_dates) == len(quotes)
    assert (
        baseline_result.acceptance.max_abs_repricing_error_bp
        <= baseline_result.acceptance.pass_tolerance_bp
    )


def test_solver_failure_is_distinct_from_acceptance(
    baseline_result,
    quotes,
    calendar,
) -> None:
    failed_calibration = replace(
        baseline_result.calibration_result,
        success=False,
    )

    acceptance = assess_baseline_calibration(
        calibration_result=failed_calibration,
        quotes=quotes,
        calendar=calendar,
    )

    assert not acceptance.calibration_success
    assert not acceptance.accepted_for_use
    assert "CALIBRATION_SOLVER_FAILED" in acceptance.issues


def test_curve_unavailable_is_rejected_without_exception(
    baseline_result,
    quotes,
    calendar,
) -> None:
    missing_curve = replace(
        baseline_result.calibration_result,
        curve=None,
    )

    acceptance = assess_baseline_calibration(
        calibration_result=missing_curve,
        quotes=quotes,
        calendar=calendar,
    )

    assert acceptance.calibration_success
    assert not acceptance.structural_valid
    assert not acceptance.accepted_for_use
    assert "CURVE_UNAVAILABLE" in acceptance.issues

def test_baseline_public_signature_remains_fixed():
    from inspect import Parameter, signature

    parameters = signature(build_baseline_ftiie_curve).parameters
    assert tuple(parameters) == ('quotes', 'calendar', 'initial_discount_factors')
    assert all(p.kind is Parameter.KEYWORD_ONLY for p in parameters.values())
    assert parameters['initial_discount_factors'].default is None
