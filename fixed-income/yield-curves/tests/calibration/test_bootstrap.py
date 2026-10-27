from datetime import date
from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.instruments import (
    build_ftiie_ois,
)
from yield_curves.pricing import (
    calculate_par_rate,
)
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


def test_bootstrap_creates_one_node_per_quote(
    quotes,
    bootstrap_result,
) -> None:
    assert len(
        bootstrap_result.curve.node_dates
    ) == len(quotes)

    assert len(
        bootstrap_result.steps
    ) == len(quotes)


def test_all_nodes_are_positive(
    bootstrap_result,
) -> None:
    assert all(
        df > 0
        for df in (
            bootstrap_result
            .curve
            .discount_factors
        )
    )


def test_pillar_dates_are_strictly_increasing(
    bootstrap_result,
) -> None:
    dates = (
        bootstrap_result
        .curve
        .node_dates
    )

    assert all(
        later > earlier
        for earlier, later in zip(
            dates,
            dates[1:],
        )
    )


def test_all_solver_steps_converge(
    bootstrap_result,
) -> None:
    assert all(
        step.converged
        for step in bootstrap_result.steps
    )


def test_all_calibration_quotes_reprice(
    bootstrap_result,
) -> None:
    for step in bootstrap_result.steps:
        assert abs(
            step.quote_error_bp
        ) <= 0.01


def test_calibrated_instruments_reprice_from_final_curve(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    curve = bootstrap_result.curve

    for quote in quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        model_quote = calculate_par_rate(
            ois=ois,
            projection_curve=curve,
            discount_curve=curve,
        )

        error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000

        assert abs(
            error_bp
        ) <= 0.01


def test_curve_reference_date_matches_effective_date(
    quotes,
    bootstrap_result,
) -> None:
    assert (
        bootstrap_result
        .curve
        .reference_date
        ==
        quotes[0].effective_date
    )


def test_curve_does_not_extend_beyond_last_pillar(
    bootstrap_result,
) -> None:
    curve = bootstrap_result.curve

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            date(
                curve.last_node_date.year + 1,
                curve.last_node_date.month,
                curve.last_node_date.day,
            )
        )


@pytest.mark.parametrize("scenario,message,brent_calls", [
    pytest.param("nonfinite", "Non-finite bootstrap objective for 1M", 0, id="nonfinite-endpoint"),
    pytest.param("no-bracket", "Bootstrap root is not bracketed for 1M", 0, id="no-sign-change"),
    pytest.param("not-converged", "Bootstrap solver did not converge for 1M", 1, id="not-converged"),
    pytest.param("nan-root", "Bootstrap produced invalid discount factor for 1M", 1, id="nan-root"),
    pytest.param("zero-root", "Bootstrap produced invalid discount factor for 1M", 1, id="zero-root"),
])
def test_sequential_rejects_invalid_objective_or_root_without_retry(
    monkeypatch, quotes, calendar, scenario, message, brent_calls,
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from yield_curves import bootstrap, calibration
    from yield_curves.curves import LogLinearDiscountCurve

    quote = quotes[0]
    expected_ois = build_ftiie_ois(
        trade_date=quote.trade_date, maturity_date=quote.contractual_maturity_date,
        fixed_rate=quote.par_rate, notional=1.0, calendar=calendar,
    )
    evaluated_dfs = []

    def adverse_valuation(*, ois, projection_curve, discount_curve):
        assert ois == expected_ois
        assert projection_curve is discount_curve
        assert type(projection_curve) is LogLinearDiscountCurve
        candidate_df, = projection_curve.discount_factors
        evaluated_dfs.append(candidate_df)
        if scenario == "nonfinite" and candidate_df == 1e-6:
            npv = float("nan")
        elif scenario == "no-bracket":
            npv = 1.0
        else:
            npv = candidate_df - 1.0
        return SimpleNamespace(npv_receive_float_pay_fixed=npv)

    def invalid_root(objective, lower, upper, **kwargs):
        assert brent_calls == 1, "Invalid endpoints reached Brent"
        assert (lower, upper) == (1e-6, 2.0)
        root = {"not-converged": 0.99, "nan-root": float("nan"), "zero-root": 0.0}[scenario]
        return root, SimpleNamespace(
            converged=scenario != "not-converged", iterations=2, function_calls=3,
        )

    brent = Mock(side_effect=invalid_root)
    other_solver = Mock(side_effect=AssertionError("Sequential failure reached another solver"))
    monkeypatch.setattr(bootstrap, "value_ftiie_ois", adverse_valuation)
    monkeypatch.setattr(bootstrap, "brentq", brent)
    monkeypatch.setattr(calibration, "least_squares", other_solver)

    with pytest.raises(RuntimeError, match=message) as error:
        bootstrap.bootstrap_ftiie_ois_curve(quotes=quotes[:1], calendar=calendar)

    assert evaluated_dfs == [1e-6, 2.0]
    assert brent.call_count == brent_calls
    other_solver.assert_not_called()
    if scenario == "no-bracket":
        assert "NPV(1e-06)=1" in str(error.value)
        assert "NPV(2.0)=1" in str(error.value)
    elif scenario in ("nan-root", "zero-root"):
        assert str(error.value).endswith("nan." if scenario == "nan-root" else "0.0.")


@pytest.mark.parametrize("root,brent_calls,iterations,function_calls", [
    pytest.param(1e-6, 0, 0, 1, id="lower-endpoint"),
    pytest.param(2.0, 0, 0, 1, id="upper-endpoint"),
    pytest.param(0.9, 1, 7, 13, id="interior-brent"),
])
def test_sequential_root_diagnostics_distinguish_endpoint_and_brent(
    monkeypatch, quotes, calendar, root, brent_calls, iterations, function_calls,
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from yield_curves import bootstrap, calibration
    from yield_curves.curves import CurveInterpolationMethod, LogLinearDiscountCurve

    lower, upper = 1e-6, 2.0
    quote = quotes[0]
    expected_ois = build_ftiie_ois(
        trade_date=quote.trade_date, maturity_date=quote.contractual_maturity_date,
        fixed_rate=quote.par_rate, notional=1.0, calendar=calendar,
    )
    evaluated_dfs = []

    def controlled_valuation(*, ois, projection_curve, discount_curve):
        assert ois == expected_ois
        assert projection_curve is discount_curve
        assert type(projection_curve) is LogLinearDiscountCurve
        assert projection_curve.reference_date == expected_ois.effective_date
        assert projection_curve.node_dates == (expected_ois.final_payment_date,)
        candidate_df, = projection_curve.discount_factors
        evaluated_dfs.append(candidate_df)
        return SimpleNamespace(npv_receive_float_pay_fixed=candidate_df - root)

    def interior_brent(objective, bracket_lower, bracket_upper, **kwargs):
        assert (bracket_lower, bracket_upper) == (lower, upper)
        assert kwargs == {
            "xtol": 1e-14, "rtol": 1e-12, "maxiter": 200,
            "full_output": True, "disp": False,
        }
        assert lower < root < upper
        assert objective(root) == 0.0
        return root, SimpleNamespace(converged=True, iterations=7, function_calls=11)

    brent = Mock(side_effect=(
        interior_brent if brent_calls else AssertionError("Endpoint root reached Brent")
    ))
    other_solver = Mock(side_effect=AssertionError("Sequential solve reached another solver"))
    monkeypatch.setattr(bootstrap, "value_ftiie_ois", controlled_valuation)
    # Isolate final repricing from the artificial DF=2 / DF=1e-6 endpoints.
    monkeypatch.setattr(bootstrap, "calculate_par_rate", Mock(return_value=quote.par_rate))
    monkeypatch.setattr(bootstrap, "brentq", brent)
    monkeypatch.setattr(calibration, "least_squares", other_solver)

    result = bootstrap.bootstrap_ftiie_ois_curve(quotes=quotes[:1], calendar=calendar)

    assert len(result.steps) == 1
    step, = result.steps
    assert step.tenor == quote.tenor
    assert step.pillar_date == expected_ois.final_payment_date
    assert step.solved_discount_factor == root
    assert step.npv_at_solution == 0.0
    assert (step.bracket_lower_df, step.bracket_upper_df) == (lower, upper)
    assert step.iterations == iterations
    # Reported diagnostics differ from physical valuation calls: endpoints
    # report 1 despite both bracket evaluations; Brent reports its own calls + 2.
    assert step.function_calls == function_calls
    assert step.converged is True
    assert result.interpolation_method is CurveInterpolationMethod.LOG_LINEAR_DF
    assert type(result.curve) is LogLinearDiscountCurve
    assert result.curve.reference_date == expected_ois.effective_date
    assert result.curve.node_dates == (expected_ois.final_payment_date,)
    assert result.curve.discount_factors == (root,)
    assert evaluated_dfs[:2] == [lower, upper]
    assert evaluated_dfs[2:] == ([root, root] if brent_calls else [root])
    assert brent.call_count == brent_calls
    other_solver.assert_not_called()
