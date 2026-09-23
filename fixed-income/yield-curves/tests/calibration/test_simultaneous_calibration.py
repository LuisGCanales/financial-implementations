from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve_with_method,
)
from yield_curves.calibration import (
    calibrate_ftiie_ois_curve_simultaneously,
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