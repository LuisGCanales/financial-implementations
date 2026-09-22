from pathlib import Path

import pytest

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.sensitivity import (
    analyze_quote_perturbations,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
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


@pytest.fixture(scope="module")
def quotes():
    return read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )


@pytest.fixture(scope="module")
def calendar():
    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture(scope="module")
def report(
    quotes,
    calendar,
):
    return analyze_quote_perturbations(
        quotes=quotes,
        calendar=calendar,
        bump_bp=1.0,
        forward_period_days=28,
        grid_step_days=7,
    )


def test_one_perturbation_per_quote(
    quotes,
    report,
) -> None:
    assert len(
        report.perturbations
    ) == len(
        quotes
    )


def test_each_perturbation_contains_one_response_per_node(
    quotes,
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        assert len(
            perturbation
            .node_sensitivities
        ) == len(
            quotes
        )


def test_upstream_nodes_are_invariant(
    report,
) -> None:
    assert all(
        perturbation
        .upstream_invariance_pass
        for perturbation
        in report.perturbations
    )


def test_upstream_df_changes_are_numerically_negligible(
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        assert (
            perturbation
            .maximum_upstream_abs_df_change
            <= report
            .upstream_df_tolerance
        )


def test_shocked_node_changes(
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        assert abs(
            perturbation
            .own_node_delta_df
        ) > 0


def test_shocked_node_zero_rate_changes(
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        assert abs(
            perturbation
            .own_node_zero_change_bp
        ) > 0


def test_quote_bump_is_exactly_one_basis_point(
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        actual_bump_bp = (
            perturbation.shocked_quote
            - perturbation.original_quote
        ) * 10_000.0

        assert actual_bump_bp == pytest.approx(
            1.0
        )


def test_first_quote_shock_can_propagate_downstream(
    report,
) -> None:
    first_shock = (
        report.perturbations[0]
    )

    downstream_changes = [
        abs(
            sensitivity
            .delta_discount_factor
        )
        for sensitivity
        in first_shock
        .node_sensitivities
        if sensitivity.is_downstream
    ]

    assert downstream_changes

    assert any(
        change > 0
        for change in downstream_changes
    )


def test_last_quote_shock_leaves_all_previous_nodes_unchanged(
    report,
) -> None:
    last_shock = (
        report.perturbations[-1]
    )

    upstream = [
        sensitivity
        for sensitivity
        in last_shock
        .node_sensitivities
        if sensitivity.is_upstream
    ]

    assert upstream

    assert all(
        abs(
            sensitivity
            .delta_discount_factor
        )
        <= report
        .upstream_df_tolerance
        for sensitivity
        in upstream
    )


def test_each_quote_shock_changes_forward_curve(
    report,
) -> None:
    for perturbation in (
        report.perturbations
    ):
        assert (
            perturbation
            .forward_summary
            .max_abs_change_bp
            > 0
        )
        
        
from yield_curves.sensitivity import (
    analyze_central_quote_perturbations,
)


@pytest.fixture(scope="module")
def central_report(
    quotes,
    calendar,
):
    return analyze_central_quote_perturbations(
        quotes=quotes,
        calendar=calendar,
        bump_bp=1.0,
        forward_period_days=28,
        grid_step_days=7,
    )


def test_central_analysis_has_one_result_per_quote(
    quotes,
    central_report,
) -> None:
    assert len(
        central_report.perturbations
    ) == len(
        quotes
    )


def test_central_upstream_sensitivities_are_zero(
    central_report,
) -> None:
    for perturbation in (
        central_report.perturbations
    ):
        assert (
            perturbation
            .maximum_upstream_abs_sensitivity
            == pytest.approx(
                0.0,
                abs=1e-10,
            )
        )


def test_central_upstream_curvature_is_zero(
    central_report,
) -> None:
    for perturbation in (
        central_report.perturbations
    ):
        assert (
            perturbation
            .maximum_upstream_abs_curvature
            == pytest.approx(
                0.0,
                abs=1e-10,
            )
        )


def test_own_node_central_sensitivity_is_nonzero(
    central_report,
) -> None:
    for perturbation in (
        central_report.perturbations
    ):
        assert abs(
            perturbation
            .own_node_sensitivity
        ) > 0


def test_directional_responses_average_to_central_sensitivity(
    central_report,
) -> None:
    for perturbation in (
        central_report.perturbations
    ):
        for sensitivity in (
            perturbation
            .node_sensitivities
        ):
            expected = (
                sensitivity.plus_response_bp
                + sensitivity.minus_response_bp
            ) / (
                2.0
                * perturbation.bump_bp
            )

            assert (
                sensitivity
                .central_sensitivity_bp_per_bp
                == pytest.approx(
                    expected
                )
            )


def test_forward_central_sensitivity_is_nonzero(
    central_report,
) -> None:
    for perturbation in (
        central_report.perturbations
    ):
        assert (
            perturbation
            .forward_summary
            .max_abs_sensitivity
            > 0
        )


def test_forward_curvature_is_finite(
    central_report,
) -> None:
    from math import isfinite

    for perturbation in (
        central_report.perturbations
    ):
        assert isfinite(
            perturbation
            .forward_summary
            .curvature_rmse
        )