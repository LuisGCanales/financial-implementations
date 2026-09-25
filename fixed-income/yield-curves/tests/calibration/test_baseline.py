from dataclasses import replace
from pathlib import Path

import pytest

from yield_curves.baseline import (
    BASELINE_INTERPOLATION_METHOD,
    assess_baseline_calibration,
    build_baseline_ftiie_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)


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