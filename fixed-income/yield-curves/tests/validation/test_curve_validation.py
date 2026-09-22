from datetime import date
from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)
from yield_curves.validation import (
    CurveValidationStatus,
    InstrumentValidationStatus,
    ValidationIssue,
    ValidationSeverity,
    classify_repricing_error,
    validate_bootstrap_result,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


@pytest.fixture
def quotes():
    return read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )


@pytest.fixture
def calendar():
    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture
def bootstrap_result(
    quotes,
    calendar,
):
    return bootstrap_ftiie_ois_curve(
        quotes=quotes,
        calendar=calendar,
    )


def test_canonical_synthetic_curve_is_valid(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
    )

    assert (
        report.status
        == CurveValidationStatus.VALID
    )

    assert report.critical_issue_count == 0
    assert report.warning_count == 0


def test_all_canonical_quotes_pass_repricing(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
    )

    assert len(
        report.instrument_checks
    ) == len(
        quotes
    )

    assert all(
        check.status
        == InstrumentValidationStatus.PASS
        for check in report.instrument_checks
    )


def test_canonical_curve_has_one_node_per_quote(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
    )

    assert report.quote_count == len(
        quotes
    )

    assert report.node_count == len(
        quotes
    )


def test_all_solver_steps_are_counted(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
    )

    assert (
        report.converged_step_count
        == len(quotes)
    )


def test_repricing_threshold_pass() -> None:
    status = classify_repricing_error(
        absolute_error_bp=0.005,
        pass_tolerance_bp=0.01,
        fail_tolerance_bp=0.10,
    )

    assert (
        status
        == InstrumentValidationStatus.PASS
    )


def test_repricing_threshold_review() -> None:
    status = classify_repricing_error(
        absolute_error_bp=0.05,
        pass_tolerance_bp=0.01,
        fail_tolerance_bp=0.10,
    )

    assert (
        status
        == InstrumentValidationStatus.REVIEW
    )


def test_repricing_threshold_fail() -> None:
    status = classify_repricing_error(
        absolute_error_bp=0.20,
        pass_tolerance_bp=0.01,
        fail_tolerance_bp=0.10,
    )

    assert (
        status
        == InstrumentValidationStatus.FAIL
    )


def test_warning_changes_curve_to_review(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    warning = ValidationIssue(
        code="TEST_WARNING",
        severity=ValidationSeverity.WARNING,
        message="Synthetic validation warning.",
    )

    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
        additional_issues=(
            warning,
        ),
    )

    assert (
        report.status
        == CurveValidationStatus.REVIEW
    )

    assert report.warning_count == 1


def test_critical_issue_changes_curve_to_invalid(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    critical = ValidationIssue(
        code="TEST_CRITICAL",
        severity=ValidationSeverity.CRITICAL,
        message="Synthetic critical failure.",
    )

    report = validate_bootstrap_result(
        bootstrap_result=bootstrap_result,
        quotes=quotes,
        calendar=calendar,
        additional_issues=(
            critical,
        ),
    )

    assert (
        report.status
        == CurveValidationStatus.INVALID
    )

    assert report.critical_issue_count == 1