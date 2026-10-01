from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
    bootstrap_ftiie_ois_curve_with_method,
)
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.curves import (
    CurveInterpolationMethod,
    LinearContinuousZeroCurve,
    LogLinearDiscountCurve,
)
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


def test_canonical_wrapper_still_returns_log_linear_curve(
    quotes,
    calendar,
) -> None:
    result = bootstrap_ftiie_ois_curve(
        quotes=quotes,
        calendar=calendar,
    )

    assert isinstance(
        result.curve,
        LogLinearDiscountCurve,
    )


def test_linear_zero_method_returns_expected_curve_type(
    quotes,
    calendar,
) -> None:
    result = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LINEAR_CONTINUOUS_ZERO
            ),
        )
    )

    assert isinstance(
        result.curve,
        LinearContinuousZeroCurve,
    )


@pytest.mark.parametrize(
    "method",
    (
        CurveInterpolationMethod.LOG_LINEAR_DF,
        CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    ),
)
def test_both_methods_reprice_all_calibration_quotes(
    quotes,
    calendar,
    method,
) -> None:
    result = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=method,
        )
    )

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

        model_quote = (
            calculate_par_rate(
                ois=ois,
                projection_curve=(
                    result.curve
                ),
                discount_curve=(
                    result.curve
                ),
            )
        )

        error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000.0

        assert abs(
            error_bp
        ) <= 0.01


def test_methods_use_same_pillar_dates(
    quotes,
    calendar,
) -> None:
    log_linear = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LOG_LINEAR_DF
            ),
        )
    )

    linear_zero = (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LINEAR_CONTINUOUS_ZERO
            ),
        )
    )

    assert (
        log_linear.curve.node_dates
        == linear_zero.curve.node_dates
    )


def test_capabilities_cover_every_known_method_explicitly():
    from yield_curves.engine_capabilities import (
        METHOD_CAPABILITIES, CurveConstructionEngine, supports,
    )

    expected = {
        CurveInterpolationMethod.LOG_LINEAR_DF: (True, True),
        CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO: (True, True),
        CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO: (False, True),
        CurveInterpolationMethod.PCHIP_CONTINUOUS_ZERO: (False, True),
    }
    assert set(METHOD_CAPABILITIES) == set(CurveInterpolationMethod) == set(expected)
    for method, (sequential, simultaneous) in expected.items():
        assert supports(method, CurveConstructionEngine.SEQUENTIAL) is sequential
        assert supports(method, CurveConstructionEngine.SIMULTANEOUS) is simultaneous


def test_capability_map_and_descriptors_are_immutable():
    from dataclasses import FrozenInstanceError
    from yield_curves.engine_capabilities import METHOD_CAPABILITIES

    method = CurveInterpolationMethod.LOG_LINEAR_DF
    with pytest.raises(TypeError):
        METHOD_CAPABILITIES[method] = METHOD_CAPABILITIES[method]
    with pytest.raises(FrozenInstanceError):
        METHOD_CAPABILITIES[method].sequential = False


@pytest.mark.parametrize("engine", ("sequential bootstrap", "simultaneous nodal calibration"))
def test_unknown_method_has_no_capability(engine):
    from yield_curves.engine_capabilities import supports

    with pytest.raises(ValueError, match="Unknown interpolation method"):
        supports("UNKNOWN", engine)


def test_unknown_engine_is_rejected():
    from yield_curves.engine_capabilities import supports

    with pytest.raises(ValueError):
        supports(CurveInterpolationMethod.LOG_LINEAR_DF, "UNKNOWN")


@pytest.mark.parametrize("method, message", (
    (CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO, "not supported.*sequential bootstrap"),
    (CurveInterpolationMethod.PCHIP_CONTINUOUS_ZERO, "not supported.*sequential bootstrap"),
    ("UNKNOWN", "Unknown interpolation method"),
))
def test_sequential_rejects_before_preparation_or_solve(monkeypatch, quotes, calendar, method, message):
    import yield_curves.bootstrap as engine

    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported method reached preparation or solver")

    monkeypatch.setattr(engine, "brentq", forbidden)
    monkeypatch.setattr(engine, "build_calibration_ftiie_ois", forbidden)
    with pytest.raises(ValueError, match=message):
        engine.bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes[:2], calendar=calendar, interpolation_method=method,
        )
