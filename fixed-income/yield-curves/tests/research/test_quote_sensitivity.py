from dataclasses import fields, replace
from datetime import date
from types import SimpleNamespace

from yield_curves.calendars import BusinessCalendar
from yield_curves.quotes import OISQuote, bump_ois_quotes
from yield_curves.research import sensitivity
from yield_curves.research.global_sensitivity import _perturb_quotes

from pathlib import Path

import pytest

from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.research.sensitivity import (analyze_quote_perturbations)
from yield_curves.research.synthetic import (read_synthetic_ois_quotes_csv)


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


@pytest.mark.slow
def test_one_perturbation_per_quote(
    quotes,
    report,
) -> None:
    assert len(
        report.perturbations
    ) == len(
        quotes
    )


@pytest.mark.slow
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


@pytest.mark.slow
def test_upstream_nodes_are_invariant(
    report,
) -> None:
    assert all(
        perturbation
        .upstream_invariance_pass
        for perturbation
        in report.perturbations
    )


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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
        
        
from yield_curves.research.sensitivity import (analyze_central_quote_perturbations)


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


@pytest.mark.slow
def test_central_analysis_has_one_result_per_quote(
    quotes,
    central_report,
) -> None:
    assert len(
        central_report.perturbations
    ) == len(
        quotes
    )


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
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

# Small P08 contract checks: never request the full report fixtures above.


@pytest.fixture
def neutral_quotes():
    return (
        OISQuote('1M', date(2026, 1, 5), date(2026, 2, 7), 0.08),
        OISQuote('3M', date(2026, 1, 5), date(2026, 4, 7), 0.081),
    )


@pytest.mark.parametrize('transform', [
    bump_ois_quotes, sensitivity._build_perturbed_quotes, _perturb_quotes,
])
@pytest.mark.parametrize('shock_index', [0, 1])
@pytest.mark.parametrize('bump_bp', [1.0, -1.0, 2.5, 0.0])
def test_neutral_bump_values(transform, shock_index, bump_bp, neutral_quotes):
    # Exercise the structural protocol, including research-only metadata.
    originals = [SimpleNamespace(**{
        field.name: getattr(quote, field.name) for field in fields(OISQuote)
    }, scenario_id='research-only') for quote in neutral_quotes]
    result = transform(quotes=originals, shock_index=shock_index, bump_bp=bump_bp)
    expected = list(neutral_quotes)
    expected[shock_index] = replace(
        expected[shock_index], par_rate=expected[shock_index].par_rate + bump_bp / 10_000.0,
    )
    assert result == tuple(expected)
    assert all(type(quote) is OISQuote for quote in result)
    assert sum(a != b for a, b in zip(result, neutral_quotes)) == (bump_bp != 0)
    assert [quote.par_rate for quote in originals] == [q.par_rate for q in neutral_quotes]
    originals[0].par_rate = 99.0
    assert result == tuple(expected)


@pytest.mark.parametrize('transform', [
    bump_ois_quotes, sensitivity._build_perturbed_quotes, _perturb_quotes,
])
@pytest.mark.parametrize('index', [-1, 2])
def test_neutral_bump_bad_index(transform, index, neutral_quotes):
    with pytest.raises(IndexError, match='Shock index'):
        transform(quotes=neutral_quotes, shock_index=index, bump_bp=1.0)


@pytest.mark.parametrize('transform,error', [
    (bump_ois_quotes, IndexError),
    (sensitivity._build_perturbed_quotes, ValueError),
    (_perturb_quotes, IndexError),
])
def test_neutral_bump_empty_preserves_failure(transform, error):
    with pytest.raises(error):
        transform(quotes=(), shock_index=0, bump_bp=1.0)


@pytest.mark.parametrize('transform', [
    bump_ois_quotes, sensitivity._build_perturbed_quotes, _perturb_quotes,
])
@pytest.mark.parametrize('bump', [float('nan'), float('inf'), -float('inf'), 'bad', None])
def test_neutral_bump_invalid_shock(transform, bump, neutral_quotes):
    with pytest.raises((ValueError, TypeError)):
        transform(quotes=neutral_quotes, shock_index=0, bump_bp=bump)


@pytest.mark.parametrize('transform', [
    bump_ois_quotes, sensitivity._build_perturbed_quotes, _perturb_quotes,
])
def test_neutral_bump_preserves_tenor_validation_boundary(transform, neutral_quotes):
    # Shocks select an index, not a parsed tenor. Invalid labels stay untouched;
    # operational preflight still owns their rejection.
    from yield_curves.inputs import prepare_baseline_inputs, BaselineInputError

    invalid = (replace(neutral_quotes[0], tenor=''), neutral_quotes[1])
    result = transform(quotes=invalid, shock_index=0, bump_bp=1.0)
    assert result[0].tenor == ''
    calendar = BusinessCalendar('test', frozenset(), coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31))
    for quotes in (invalid, result):
        with pytest.raises(BaselineInputError, match='INVALID_TENOR'):
            prepare_baseline_inputs(quotes=quotes, calendar=calendar)


@pytest.mark.parametrize('analyze,directions', [
    (sensitivity.analyze_quote_perturbations, (1.0,)),
    (sensitivity.analyze_central_quote_perturbations, (1.0, -1.0)),
])
def test_neutral_quotes_reach_sequential_engine(monkeypatch, neutral_quotes, analyze, directions):
    actual = sensitivity.bootstrap_ftiie_ois_curve
    calls = []

    def capture(**kwargs):
        calls.append(tuple(kwargs['quotes']))
        return actual(**kwargs)

    monkeypatch.setattr(sensitivity, 'bootstrap_ftiie_ois_curve', capture)
    result = analyze(quotes=neutral_quotes, calendar=BusinessCalendar('test', frozenset()))
    expected = [neutral_quotes]
    for index in range(len(neutral_quotes)):
        for direction in directions:
            bumped = list(neutral_quotes)
            bumped[index] = replace(bumped[index], par_rate=bumped[index].par_rate + direction / 10_000.0)
            expected.append(tuple(bumped))
    assert calls == expected
    assert all(type(q) is OISQuote for call in calls[1:] for q in call)
    assert [(p.shock_index, p.shock_tenor, p.bump_bp) for p in result.perturbations] == [
        (index, q.tenor, 1.0) for index, q in enumerate(neutral_quotes)
    ]


@pytest.mark.parametrize('analyze,bump,message', [
    (sensitivity.analyze_quote_perturbations, 0.0, 'cannot be zero'),
    (sensitivity.analyze_central_quote_perturbations, 0.0, 'must be positive'),
    (sensitivity.analyze_central_quote_perturbations, -1.0, 'must be positive'),
])
def test_neutral_analysis_invalid_shock_before_engine(monkeypatch, neutral_quotes, analyze, bump, message):
    def unexpected(**kwargs):
        pytest.fail('Invalid shock reached the calibration engine')

    monkeypatch.setattr(sensitivity, 'bootstrap_ftiie_ois_curve', unexpected)
    with pytest.raises(ValueError, match=message):
        analyze(quotes=neutral_quotes, calendar=BusinessCalendar('test', frozenset()), bump_bp=bump)
