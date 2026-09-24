"""Tests for global simultaneous-calibration sensitivity diagnostics."""

from __future__ import annotations

from datetime import date, timedelta
from math import fsum, isfinite, sqrt
from pathlib import Path
from time import perf_counter

import pytest

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.global_sensitivity import (
    _calculate_forward_sensitivity,
    _forward_start_dates,
    _perturb_quotes,
    analyze_global_quote_sensitivity,
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
    """Load the frozen synthetic F-TIIE OIS quote set."""

    return read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )


@pytest.fixture(scope="module")
def calendar():
    """Build the projected MXMC calendar used by the experiment."""

    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture(scope="module")
def cubic_global_report(
    quotes,
    calendar,
):
    """Run the expensive global sensitivity experiment once.

    Cubic continuous-zero interpolation is used because it is the
    primary globally coupled interpolation challenger.

    Progress is printed when pytest capture is disabled, for example:

        pytest -s -vv tests/validation/test_global_sensitivity.py
    """

    started = perf_counter()

    def progress(message: str) -> None:
        elapsed = (
            perf_counter()
            - started
        )

        print(
            f"[cubic_global_report +{elapsed:8.2f}s] "
            f"{message}",
            flush=True,
        )

    progress(
        "starting full cubic global-sensitivity fixture"
    )

    report = analyze_global_quote_sensitivity(
        quotes=quotes,
        calendar=calendar,
        interpolation_method=(
            CurveInterpolationMethod
            .CUBIC_CONTINUOUS_ZERO
        ),
        bump_bp=1.0,
        forward_period_days=28,
        grid_step_days=7,
        progress_callback=progress,
    )

    progress(
        "finished full cubic global-sensitivity fixture"
    )

    return report


class ConstantForwardCurve:
    """Minimal curve stub returning one constant forward rate."""

    def __init__(
        self,
        forward_rate: float,
    ) -> None:
        self._forward_rate = (
            forward_rate
        )

    def forward_rate(
        self,
        start_date,
        end_date,
    ) -> float:
        del start_date
        del end_date

        return (
            self._forward_rate
        )


def test_perturb_quotes_changes_only_selected_quote(
    quotes,
) -> None:
    shock_index = 3
    bump_bp = 1.0

    perturbed = _perturb_quotes(
        quotes=quotes,
        shock_index=shock_index,
        bump_bp=bump_bp,
    )

    assert len(
        perturbed
    ) == len(
        quotes
    )

    for index, (
        original,
        shocked,
    ) in enumerate(
        zip(
            quotes,
            perturbed,
        )
    ):
        assert (
            shocked.tenor
            == original.tenor
        )

        assert (
            shocked.trade_date
            == original.trade_date
        )

        assert (
            shocked.contractual_maturity_date
            == original.contractual_maturity_date
        )

        expected_rate = (
            original.par_rate
            + (
                0.0001
                if index == shock_index
                else 0.0
            )
        )

        assert shocked.par_rate == pytest.approx(
            expected_rate
        )


def test_perturb_quotes_supports_negative_bump(
    quotes,
) -> None:
    shock_index = 2

    perturbed = _perturb_quotes(
        quotes=quotes,
        shock_index=shock_index,
        bump_bp=-1.0,
    )

    assert (
        perturbed[
            shock_index
        ].par_rate
        == pytest.approx(
            quotes[
                shock_index
            ].par_rate
            - 0.0001
        )
    )


def test_perturb_quotes_rejects_negative_index(
    quotes,
) -> None:
    with pytest.raises(
        IndexError,
        match="Shock index",
    ):
        _perturb_quotes(
            quotes=quotes,
            shock_index=-1,
            bump_bp=1.0,
        )


def test_perturb_quotes_rejects_index_past_end(
    quotes,
) -> None:
    with pytest.raises(
        IndexError,
        match="Shock index",
    ):
        _perturb_quotes(
            quotes=quotes,
            shock_index=len(
                quotes
            ),
            bump_bp=1.0,
        )


def test_forward_start_dates_builds_expected_grid(
) -> None:
    reference_date = date(
        2026,
        1,
        1,
    )

    last_date = date(
        2026,
        2,
        26,
    )

    dates = _forward_start_dates(
        reference_date=reference_date,
        last_date=last_date,
        forward_period_days=28,
        grid_step_days=7,
    )

    assert dates == (
        date(
            2026,
            1,
            1,
        ),
        date(
            2026,
            1,
            8,
        ),
        date(
            2026,
            1,
            15,
        ),
        date(
            2026,
            1,
            22,
        ),
        date(
            2026,
            1,
            29,
        ),
    )


def test_forward_start_dates_rejects_nonpositive_forward_period(
) -> None:
    with pytest.raises(
        ValueError,
        match="Forward period",
    ):
        _forward_start_dates(
            reference_date=date(
                2026,
                1,
                1,
            ),
            last_date=date(
                2027,
                1,
                1,
            ),
            forward_period_days=0,
            grid_step_days=7,
        )


def test_forward_start_dates_rejects_nonpositive_grid_step(
) -> None:
    with pytest.raises(
        ValueError,
        match="Grid step",
    ):
        _forward_start_dates(
            reference_date=date(
                2026,
                1,
                1,
            ),
            last_date=date(
                2027,
                1,
                1,
            ),
            forward_period_days=28,
            grid_step_days=0,
        )


def test_forward_start_dates_rejects_invalid_curve_horizon(
) -> None:
    with pytest.raises(
        ValueError,
        match="Last supported date",
    ):
        _forward_start_dates(
            reference_date=date(
                2026,
                1,
                1,
            ),
            last_date=date(
                2026,
                1,
                1,
            ),
            forward_period_days=28,
            grid_step_days=7,
        )


def test_forward_start_dates_rejects_horizon_shorter_than_forward_period(
) -> None:
    with pytest.raises(
        ValueError,
        match="Curve horizon",
    ):
        _forward_start_dates(
            reference_date=date(
                2026,
                1,
                1,
            ),
            last_date=date(
                2026,
                1,
                15,
            ),
            forward_period_days=28,
            grid_step_days=7,
        )


def test_calculate_forward_sensitivity_exact_linear_response(
) -> None:
    """A symmetric +/-1 bp forward shift gives unit sensitivity."""

    dates = (
        date(
            2026,
            1,
            1,
        ),
        date(
            2026,
            1,
            8,
        ),
        date(
            2026,
            1,
            15,
        ),
    )

    base_curve = ConstantForwardCurve(
        0.05
    )

    plus_curve = ConstantForwardCurve(
        0.0501
    )

    minus_curve = ConstantForwardCurve(
        0.0499
    )

    result = (
        _calculate_forward_sensitivity(
            base_curve=base_curve,
            plus_curve=plus_curve,
            minus_curve=minus_curve,
            dates=dates,
            bump_bp=1.0,
            forward_period_days=28,
        )
    )

    assert (
        result.observation_count
        == 3
    )

    assert (
        result.sensitivity_bias
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.sensitivity_mae
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.sensitivity_rmse
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.maximum_abs_sensitivity
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.maximum_abs_sensitivity_date
        == dates[0]
    )

    assert (
        result.curvature_rmse
        == pytest.approx(
            0.0,
            abs=1e-12,
        )
    )

    assert (
        result.maximum_abs_curvature
        == pytest.approx(
            0.0,
            abs=1e-12,
        )
    )

    assert (
        result.maximum_abs_curvature_date
        == dates[0]
    )

    assert len(
        result.observations
    ) == 3

    for observation, start_date in zip(
        result.observations,
        dates,
    ):
        assert (
            observation.start_date
            == start_date
        )

        assert (
            observation.end_date
            == start_date
            + timedelta(
                days=28
            )
        )

        assert (
            observation.base_forward_rate
            == pytest.approx(
                0.05
            )
        )

        assert (
            observation.plus_forward_rate
            == pytest.approx(
                0.0501
            )
        )

        assert (
            observation.minus_forward_rate
            == pytest.approx(
                0.0499
            )
        )

        assert (
            observation
            .central_sensitivity_bp_per_bp
            == pytest.approx(
                1.0
            )
        )

        assert (
            observation.curvature_bp_per_bp2
            == pytest.approx(
                0.0,
                abs=1e-12,
            )
        )


def test_calculate_forward_sensitivity_detects_curvature(
) -> None:
    """Asymmetric +/- shocks produce nonzero local curvature."""

    dates = (
        date(
            2026,
            1,
            1,
        ),
    )

    result = (
        _calculate_forward_sensitivity(
            base_curve=(
                ConstantForwardCurve(
                    0.05
                )
            ),
            plus_curve=(
                ConstantForwardCurve(
                    0.0502
                )
            ),
            minus_curve=(
                ConstantForwardCurve(
                    0.0499
                )
            ),
            dates=dates,
            bump_bp=1.0,
            forward_period_days=28,
        )
    )

    # Central sensitivity:
    #
    # (0.0502 - 0.0499) * 10,000 / 2 = 1.5
    assert (
        result.sensitivity_rmse
        == pytest.approx(
            1.5
        )
    )

    # Curvature:
    #
    # (0.0502 - 2*0.05 + 0.0499) * 10,000 = 1.0
    assert (
        result.curvature_rmse
        == pytest.approx(
            1.0
        )
    )

    assert (
        result.maximum_abs_curvature
        == pytest.approx(
            1.0
        )
    )


def test_calculate_forward_sensitivity_rejects_empty_dates(
) -> None:
    curve = ConstantForwardCurve(
        0.05
    )

    with pytest.raises(
        ValueError,
        match="at least one observation",
    ):
        _calculate_forward_sensitivity(
            base_curve=curve,
            plus_curve=curve,
            minus_curve=curve,
            dates=(),
            bump_bp=1.0,
            forward_period_days=28,
        )


def test_calculate_forward_sensitivity_rejects_nonpositive_bump(
) -> None:
    curve = ConstantForwardCurve(
        0.05
    )

    with pytest.raises(
        ValueError,
        match="Sensitivity bump",
    ):
        _calculate_forward_sensitivity(
            base_curve=curve,
            plus_curve=curve,
            minus_curve=curve,
            dates=(
                date(
                    2026,
                    1,
                    1,
                ),
            ),
            bump_bp=0.0,
            forward_period_days=28,
        )


@pytest.mark.slow
def test_global_sensitivity_report_metadata(
    cubic_global_report,
    quotes,
) -> None:
    report = (
        cubic_global_report
    )

    assert (
        report.interpolation_method
        is CurveInterpolationMethod
        .CUBIC_CONTINUOUS_ZERO
    )

    assert (
        report.bump_bp
        == pytest.approx(
            1.0
        )
    )

    assert (
        report.forward_period_days
        == 28
    )

    assert (
        report.grid_step_days
        == 7
    )

    assert (
        report.base_calibration.success
        is True
    )

    assert len(
        report.shocks
    ) == len(
        quotes
    )


@pytest.mark.slow
def test_global_sensitivity_shock_identity_and_dimensions(
    cubic_global_report,
    quotes,
) -> None:
    report = (
        cubic_global_report
    )

    for shock_index, (
        quote,
        shock,
    ) in enumerate(
        zip(
            quotes,
            report.shocks,
        )
    ):
        assert (
            shock.shock_index
            == shock_index
        )

        assert (
            shock.shock_tenor
            == quote.tenor
        )

        assert (
            shock.bump_bp
            == pytest.approx(
                report.bump_bp
            )
        )

        assert len(
            shock.node_sensitivities
        ) == len(
            quotes
        )


@pytest.mark.slow
def test_global_node_sensitivity_coordinates_are_consistent(
    cubic_global_report,
    quotes,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        for node_index, (
            quote,
            node,
        ) in enumerate(
            zip(
                quotes,
                shock.node_sensitivities,
            )
        ):
            assert (
                node.shock_index
                == shock.shock_index
            )

            assert (
                node.shock_tenor
                == shock.shock_tenor
            )

            assert (
                node.node_index
                == node_index
            )

            assert (
                node.node_tenor
                == quote.tenor
            )

            assert (
                node.maturity_distance
                == (
                    node_index
                    - shock.shock_index
                )
            )

            assert isfinite(
                node.central_sensitivity_bp_per_bp
            )

            assert isfinite(
                node.curvature_bp_per_bp2
            )


@pytest.mark.slow
def test_global_own_node_metrics_match_diagonal(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        diagonal = (
            shock.node_sensitivities[
                shock.shock_index
            ]
        )

        assert (
            shock.own_node_sensitivity
            == pytest.approx(
                diagonal
                .central_sensitivity_bp_per_bp
            )
        )

        assert (
            shock.own_node_curvature
            == pytest.approx(
                diagonal
                .curvature_bp_per_bp2
            )
        )


@pytest.mark.slow
def test_global_aggregate_node_sensitivity_metrics_are_consistent(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        absolute_values = [
            abs(
                item
                .central_sensitivity_bp_per_bp
            )
            for item in (
                shock.node_sensitivities
            )
        ]

        total_abs = fsum(
            absolute_values
        )

        own_abs = (
            absolute_values[
                shock.shock_index
            ]
        )

        off_diagonal_abs = (
            total_abs
            - own_abs
        )

        assert (
            shock.total_abs_node_sensitivity
            == pytest.approx(
                total_abs
            )
        )

        assert (
            shock.off_diagonal_abs_sensitivity
            == pytest.approx(
                off_diagonal_abs
            )
        )

        expected_share = (
            0.0
            if total_abs == 0.0
            else (
                off_diagonal_abs
                / total_abs
            )
        )

        assert (
            shock.off_diagonal_share
            == pytest.approx(
                expected_share
            )
        )

        assert (
            0.0
            <= shock.off_diagonal_share
            <= 1.0
        )


@pytest.mark.slow
def test_global_maximum_node_sensitivity_is_consistent(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        maximum_node = max(
            shock.node_sensitivities,
            key=lambda item: abs(
                item
                .central_sensitivity_bp_per_bp
            ),
        )

        assert (
            shock.maximum_abs_node_sensitivity
            == pytest.approx(
                abs(
                    maximum_node
                    .central_sensitivity_bp_per_bp
                )
            )
        )

        assert (
            shock.maximum_abs_node_sensitivity_tenor
            == maximum_node.node_tenor
        )


@pytest.mark.slow
def test_perturbed_global_calibrations_succeed_and_reprice(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        assert (
            shock.plus_calibration_success
            is True
        )

        assert (
            shock.minus_calibration_success
            is True
        )

        assert isfinite(
            shock.plus_max_abs_repricing_error_bp
        )

        assert isfinite(
            shock.minus_max_abs_repricing_error_bp
        )

        # Project calibration PASS threshold.
        assert (
            shock.plus_max_abs_repricing_error_bp
            <= 0.01
        )

        assert (
            shock.minus_max_abs_repricing_error_bp
            <= 0.01
        )


@pytest.mark.slow
def test_global_forward_observations_are_structurally_consistent(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        forward = (
            shock.forward_sensitivity
        )

        assert (
            forward.observation_count
            == len(
                forward.observations
            )
        )

        assert (
            forward.observation_count
            > 0
        )

        previous_start = None

        for observation in (
            forward.observations
        ):
            assert (
                observation.end_date
                - observation.start_date
                == timedelta(
                    days=(
                        report
                        .forward_period_days
                    )
                )
            )

            if previous_start is not None:
                assert (
                    observation.start_date
                    - previous_start
                    == timedelta(
                        days=(
                            report
                            .grid_step_days
                        )
                    )
                )

            previous_start = (
                observation.start_date
            )

            assert isfinite(
                observation.base_forward_rate
            )

            assert isfinite(
                observation.plus_forward_rate
            )

            assert isfinite(
                observation.minus_forward_rate
            )

            assert isfinite(
                observation
                .central_sensitivity_bp_per_bp
            )

            assert isfinite(
                observation.curvature_bp_per_bp2
            )


@pytest.mark.slow
def test_global_forward_summary_matches_dense_observations(
    cubic_global_report,
) -> None:
    report = (
        cubic_global_report
    )

    for shock in (
        report.shocks
    ):
        forward = (
            shock.forward_sensitivity
        )

        sensitivities = [
            observation
            .central_sensitivity_bp_per_bp
            for observation in (
                forward.observations
            )
        ]

        curvatures = [
            observation.curvature_bp_per_bp2
            for observation in (
                forward.observations
            )
        ]

        count = len(
            sensitivities
        )

        expected_bias = (
            fsum(
                sensitivities
            )
            / count
        )

        expected_mae = (
            fsum(
                abs(value)
                for value in sensitivities
            )
            / count
        )

        expected_rmse = sqrt(
            fsum(
                value * value
                for value in sensitivities
            )
            / count
        )

        expected_curvature_rmse = sqrt(
            fsum(
                value * value
                for value in curvatures
            )
            / count
        )

        sensitivity_max_index = max(
            range(
                count
            ),
            key=lambda index: abs(
                sensitivities[
                    index
                ]
            ),
        )

        curvature_max_index = max(
            range(
                count
            ),
            key=lambda index: abs(
                curvatures[
                    index
                ]
            ),
        )

        assert (
            forward.sensitivity_bias
            == pytest.approx(
                expected_bias
            )
        )

        assert (
            forward.sensitivity_mae
            == pytest.approx(
                expected_mae
            )
        )

        assert (
            forward.sensitivity_rmse
            == pytest.approx(
                expected_rmse
            )
        )

        assert (
            forward.maximum_abs_sensitivity
            == pytest.approx(
                abs(
                    sensitivities[
                        sensitivity_max_index
                    ]
                )
            )
        )

        assert (
            forward.maximum_abs_sensitivity_date
            == (
                forward.observations[
                    sensitivity_max_index
                ].start_date
            )
        )

        assert (
            forward.curvature_rmse
            == pytest.approx(
                expected_curvature_rmse
            )
        )

        assert (
            forward.maximum_abs_curvature
            == pytest.approx(
                abs(
                    curvatures[
                        curvature_max_index
                    ]
                )
            )
        )

        assert (
            forward.maximum_abs_curvature_date
            == (
                forward.observations[
                    curvature_max_index
                ].start_date
            )
        )


def test_global_sensitivity_rejects_empty_quotes(
    calendar,
) -> None:
    with pytest.raises(
        ValueError,
        match="At least one calibration quote",
    ):
        analyze_global_quote_sensitivity(
            quotes=(),
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
        )


def test_global_sensitivity_rejects_nonpositive_bump(
    quotes,
    calendar,
) -> None:
    with pytest.raises(
        ValueError,
        match="Sensitivity bump",
    ):
        analyze_global_quote_sensitivity(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
            bump_bp=0.0,
        )


def test_global_sensitivity_rejects_nonpositive_forward_period(
    quotes,
    calendar,
) -> None:
    with pytest.raises(
        ValueError,
        match="Forward period",
    ):
        analyze_global_quote_sensitivity(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
            forward_period_days=0,
        )


def test_global_sensitivity_rejects_nonpositive_grid_step(
    quotes,
    calendar,
) -> None:
    with pytest.raises(
        ValueError,
        match="Grid step",
    ):
        analyze_global_quote_sensitivity(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .CUBIC_CONTINUOUS_ZERO
            ),
            grid_step_days=0,
        )