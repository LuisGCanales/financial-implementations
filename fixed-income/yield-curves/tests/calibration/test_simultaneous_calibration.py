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
