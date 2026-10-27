from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve_with_method,
)
from yield_curves.calibration import (
    calibrate_ftiie_ois_curve_simultaneously,
)
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.curves import (
    CurveInterpolationMethod,
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


@pytest.mark.parametrize(
    "method",
    (
        CurveInterpolationMethod.LOG_LINEAR_DF,
        CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    ),
)
def test_simultaneous_calibration_reprices_existing_methods(
    quotes,
    calendar,
    method,
) -> None:
    result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=method,
        )
    )

    assert result.success

    assert (
        result.max_abs_repricing_error_bp
        <= 0.01
    )


@pytest.mark.parametrize(
    "method",
    (
        CurveInterpolationMethod.LOG_LINEAR_DF,
        CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    ),
)
def test_simultaneous_and_sequential_solutions_agree(
    quotes,
    calendar,
    method,
) -> None:
    sequential = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=method,
        )
    )

    simultaneous = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=method,
        )
    )

    assert (
        simultaneous.curve.node_dates
        == sequential.curve.node_dates
    )

    for global_df, sequential_df in zip(
        simultaneous.curve.discount_factors,
        sequential.curve.discount_factors,
    ):
        assert global_df == pytest.approx(
            sequential_df,
            abs=1e-9,
        )


def test_cubic_zero_simultaneous_calibration_converges(
    quotes,
    calendar,
) -> None:
    result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
        )
    )

    assert result.success

    assert (
        result.max_abs_repricing_error_bp
        <= 0.01
    )


def test_cubic_zero_has_one_node_per_quote(
    quotes,
    calendar,
) -> None:
    result = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
        )
    )

    assert len(
        result.curve.node_dates
    ) == len(
        quotes
    )


@pytest.mark.parametrize("initial_dfs", (None, (0.99, 0.98)))
def test_unknown_method_rejected_before_warm_start_or_solve(monkeypatch, quotes, calendar, initial_dfs):
    import yield_curves.calibration as engine

    def forbidden(*args, **kwargs):
        pytest.fail("Unknown method reached preparation, warm-start or solver")

    for name in ("_prepare_global_calibration_instruments", "bootstrap_ftiie_ois_curve", "least_squares"):
        monkeypatch.setattr(engine, name, forbidden)
    with pytest.raises(ValueError, match="Unknown interpolation method"):
        engine.calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes[:2], calendar=calendar, interpolation_method="UNKNOWN",
            initial_discount_factors=initial_dfs,
        )


@pytest.mark.parametrize("method", tuple(CurveInterpolationMethod))
@pytest.mark.parametrize("explicit_start", (False, True))
def test_all_methods_preserve_warm_start_contract(monkeypatch, quotes, calendar, method, explicit_start):
    import numpy as np
    import yield_curves.calibration as engine
    from yield_curves.curves import build_nodal_curve

    small_quotes = quotes[:3]
    bootstrap = engine.bootstrap_ftiie_ois_curve(quotes=small_quotes, calendar=calendar)
    assert bootstrap.interpolation_method is CurveInterpolationMethod.LOG_LINEAR_DF
    initial_dfs = tuple(bootstrap.curve.discount_factors)
    original_solve = engine.least_squares
    bootstrap_calls = []
    solver_starts = []

    def warm_start(**kwargs):
        assert not explicit_start, "Explicit DFs must bypass sequential bootstrap"
        assert kwargs == {"quotes": small_quotes, "calendar": calendar}
        bootstrap_calls.append(kwargs)
        # Only discount factors may be consumed from the sequential result.
        from types import SimpleNamespace
        return SimpleNamespace(curve=SimpleNamespace(discount_factors=initial_dfs))

    def solve(residuals, x0, **kwargs):
        solver_starts.append(x0.copy())
        return original_solve(residuals, x0, **kwargs)

    monkeypatch.setattr(engine, "bootstrap_ftiie_ois_curve", warm_start)
    monkeypatch.setattr(engine, "least_squares", solve)
    result = engine.calibrate_ftiie_ois_curve_simultaneously(
        quotes=small_quotes, calendar=calendar, interpolation_method=method,
        initial_discount_factors=initial_dfs if explicit_start else None,
    )
    assert len(bootstrap_calls) == (0 if explicit_start else 1)
    assert len(solver_starts) == 1
    np.testing.assert_allclose(solver_starts[0], np.log(initial_dfs), rtol=1e-15, atol=0)
    assert result.success
    assert result.max_abs_repricing_error_bp <= 0.01
    assert result.interpolation_method is method
    expected_curve = build_nodal_curve(
        method=method, reference_date=result.curve.reference_date,
        node_dates=result.curve.node_dates, discount_factors=result.curve.discount_factors,
    )
    assert type(result.curve) is type(expected_curve)


@pytest.mark.parametrize("initial_dfs,message", [
    pytest.param((0.99,), "Initial discount-factor count must match", id="count"),
    pytest.param((0.0, 0.98), "finite and strictly positive", id="zero"),
    pytest.param((-0.01, 0.98), "finite and strictly positive", id="negative"),
    pytest.param((float("nan"), 0.98), "finite and strictly positive", id="nan"),
    pytest.param((float("inf"), 0.98), "finite and strictly positive", id="infinity"),
    pytest.param((1e-7, 0.98), "inside the calibration bounds", id="below-bound"),
    pytest.param((2.01, 0.98), "inside the calibration bounds", id="above-bound"),
    pytest.param(("not-a-df", 0.98), "could not convert string to float", id="conversion"),
])
def test_invalid_explicit_initial_vector_rejects_without_fallback(
    monkeypatch, quotes, calendar, initial_dfs, message,
):
    from unittest.mock import Mock
    from yield_curves import calibration as engine

    warm_start = Mock(side_effect=AssertionError("Invalid vector reached warm-start"))
    solve = Mock(side_effect=AssertionError("Invalid vector reached least_squares"))
    monkeypatch.setattr(engine, "bootstrap_ftiie_ois_curve", warm_start)
    monkeypatch.setattr(engine, "least_squares", solve)

    with pytest.raises(ValueError, match=message):
        engine.calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes[:2], calendar=calendar,
            interpolation_method=CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
            initial_discount_factors=initial_dfs,
        )

    warm_start.assert_not_called()
    solve.assert_not_called()


@pytest.mark.parametrize("failure_phase", ["warm-start", "simultaneous"])
def test_baseline_propagates_engine_failure_without_retry_or_fallback(
    monkeypatch, quotes, calendar, failure_phase,
):
    from dataclasses import replace
    from unittest.mock import Mock
    from yield_curves import baseline, calibration as engine
    from yield_curves.quotes import OISQuote

    # Reuse financial values without research metadata or calendar provenance.
    small_quotes = tuple(OISQuote(
        q.tenor, q.trade_date, q.contractual_maturity_date, q.par_rate,
    ) for q in quotes[:2])
    calendar = replace(calendar, provenance=None)
    initial_dfs = None if failure_phase == "warm-start" else (0.99, 0.98)
    failure = RuntimeError(f"Distinctive {failure_phase} failure")
    warm_start = Mock(side_effect=(
        failure if failure_phase == "warm-start"
        else AssertionError("Explicit vector reached sequential bootstrap")
    ))
    solve = Mock(side_effect=(
        failure if failure_phase == "simultaneous"
        else AssertionError("Failed warm-start reached simultaneous solver")
    ))
    calibrate = engine.calibrate_ftiie_ois_curve_simultaneously
    selected_methods = []

    def observe_engine(**kwargs):
        selected_methods.append(kwargs["interpolation_method"])
        assert kwargs["interpolation_method"] is CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO
        assert kwargs["initial_discount_factors"] == initial_dfs
        return calibrate(**kwargs)

    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously", observe_engine)
    monkeypatch.setattr(engine, "bootstrap_ftiie_ois_curve", warm_start)
    monkeypatch.setattr(engine, "least_squares", solve)

    with pytest.raises(RuntimeError) as error:
        baseline.build_baseline_ftiie_curve(
            quotes=small_quotes, calendar=calendar, initial_discount_factors=initial_dfs,
        )

    assert error.value is failure
    assert selected_methods == [CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO]
    if failure_phase == "warm-start":
        warm_start.assert_called_once_with(quotes=small_quotes, calendar=calendar)
        solve.assert_not_called()
    else:
        warm_start.assert_not_called()
        solve.assert_called_once()


def test_simultaneous_objective_and_solver_defaults_are_explicit(monkeypatch, quotes, calendar):
    import numpy as np
    from unittest.mock import Mock
    from yield_curves import calibration as engine
    from yield_curves.curves import CubicContinuousZeroCurve

    small_quotes = quotes[:2]
    initial_dfs = (0.99, 0.98)
    objective_dfs = (0.975, 0.955)
    log_dfs = np.log(objective_dfs)
    deltas = (0.000125, -0.00025)
    model_rates = {
        quote.contractual_maturity_date: quote.par_rate + delta
        for quote, delta in zip(small_quotes, deltas)
    }
    priced_maturities = []
    objective_curves = []
    failure = RuntimeError("Stop after observing simultaneous objective")

    def model_rate(*, ois, projection_curve, discount_curve):
        assert projection_curve is discount_curve
        assert type(projection_curve) is CubicContinuousZeroCurve
        np.testing.assert_allclose(projection_curve.discount_factors, np.exp(log_dfs),
                                   rtol=1e-14, atol=0)
        for node_date, expected_df in zip(projection_curve.node_dates, objective_dfs):
            assert projection_curve.discount_factor(node_date) == pytest.approx(expected_df)
        priced_maturities.append(ois.contractual_maturity_date)
        objective_curves.append(projection_curve)
        return model_rates[ois.contractual_maturity_date]

    def inspect_solve(residuals, x0, **kwargs):
        np.testing.assert_allclose(x0, np.log(initial_dfs), rtol=1e-14, atol=0)
        np.testing.assert_allclose(kwargs["bounds"], np.log((1e-6, 2.0)),
                                   rtol=1e-14, atol=0)
        assert kwargs["ftol"] == 1e-13
        assert kwargs["xtol"] == 1e-13
        assert kwargs["gtol"] == 1e-13
        assert kwargs["max_nfev"] == 5000
        np.testing.assert_allclose(residuals(log_dfs), np.asarray(deltas) * 10_000,
                                   rtol=1e-12, atol=1e-12)
        raise failure

    warm_start = Mock(side_effect=AssertionError("Explicit vector reached warm-start"))
    solve = Mock(side_effect=inspect_solve)
    monkeypatch.setattr(engine, "bootstrap_ftiie_ois_curve", warm_start)
    monkeypatch.setattr(engine, "calculate_par_rate", model_rate)
    monkeypatch.setattr(engine, "least_squares", solve)

    with pytest.raises(RuntimeError) as error:
        engine.calibrate_ftiie_ois_curve_simultaneously(
            quotes=small_quotes, calendar=calendar,
            interpolation_method=CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
            initial_discount_factors=initial_dfs,
        )

    assert error.value is failure
    solve.assert_called_once()
    warm_start.assert_not_called()
    assert priced_maturities == [q.contractual_maturity_date for q in small_quotes]
    assert objective_curves[0] is objective_curves[1]
