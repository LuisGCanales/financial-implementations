from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

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


def test_public_in_memory_consumer_needs_only_provider_contract(tmp_path):
    script = dedent("""
        from datetime import date, timedelta
        import math
        import sys
        from types import SimpleNamespace

        from yield_curves.baseline import BaselineResult, build_baseline_ftiie_curve
        from yield_curves.quotes import OISCalibrationQuote
        from yield_curves.calendars import BusinessCalendar
        from yield_curves.curves import DiscountFactorCurve

        quotes: tuple[OISCalibrationQuote, ...] = (
            SimpleNamespace(
                tenor="1M", trade_date=date(2026, 9, 15),
                contractual_maturity_date=date(2026, 10, 19), par_rate=0.05,
            ),
            SimpleNamespace(
                tenor="3M", trade_date=date(2026, 9, 15),
                contractual_maturity_date=date(2026, 12, 17), par_rate=0.051,
            ),
        )
        for quote in quotes:
            assert set(vars(quote)) == {
                "tenor", "trade_date", "contractual_maturity_date", "par_rate",
            }

        calendar = BusinessCalendar(
            name="TEST", coverage_start=date(2026, 1, 1),
            coverage_end=date(2026, 12, 31), weekend_days=frozenset({5, 6}),
            holidays=frozenset(),
        )
        result = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)

        assert isinstance(result, BaselineResult)
        assert result.calibration_result.success is True
        assert result.acceptance.calibration_success is True
        assert result.acceptance.structural_valid is True
        assert result.acceptance.accepted_for_use is True
        assert result.accepted_for_use is True
        assert result.acceptance.issues == ()

        curve = result.curve
        expected_reference = calendar.add_business_days(quotes[0].trade_date, 2)
        assert curve.reference_date == expected_reference == date(2026, 9, 17)
        assert isinstance(curve, DiscountFactorCurve)
        assert math.isclose(curve.discount_factor(curve.reference_date), 1.0)
        interior_date = curve.reference_date + timedelta(days=14)
        assert curve.reference_date < interior_date < curve.node_dates[-1]
        interior_df = curve.discount_factor(interior_date)
        assert math.isfinite(interior_df) and interior_df > 0.0

        checks = result.acceptance.checks
        assert len(checks) == len(quotes) == 2
        assert tuple(check.tenor for check in checks) == ("1M", "3M")
        assert tuple(check.market_quote for check in checks) == (0.05, 0.051)
        assert all(check.status.value == "PASS" for check in checks)

        forbidden = (
            "yield_curves.research", "yield_curves.tooling", "yield_curves.quote_io",
            "yield_curves.calendar_io", "yield_curves.execution",
            "yield_curves.snapshots", "yield_curves.snapshot_assurance",
        )
        loaded_forbidden = sorted(
            name for name in sys.modules
            if any(name == prefix or name.startswith(prefix + ".")
                   for prefix in forbidden)
        )
        assert loaded_forbidden == [], loaded_forbidden
    """)
    try:
        subprocess.run(
            [sys.executable, "-c", script], check=True, cwd=tmp_path,
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.CalledProcessError as error:
        pytest.fail(
            f"Public consumer exited with {error.returncode}\n"
            f"stdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        )
