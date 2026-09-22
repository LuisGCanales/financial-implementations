from datetime import date

import pytest

from yield_curves.curves import (
    FlatContinuousZeroCurve,
    LogLinearDiscountCurve,
)
from yield_curves.diagnostics import (
    analyze_curve,
    calculate_log_linear_forward_diagnostics,
    calculate_log_linear_segments,
)


REFERENCE_DATE = date(
    2026,
    1,
    1,
)


def test_single_log_linear_segment_has_constant_forward() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.93,
        ),
    )

    segments = (
        calculate_log_linear_segments(
            curve
        )
    )

    assert len(segments) == 1

    segment = segments[0]

    first_forward = curve.forward_rate(
        date(2026, 2, 1),
        date(2026, 2, 15),
    )

    second_forward = curve.forward_rate(
        date(2026, 8, 1),
        date(2026, 8, 15),
    )

    assert first_forward == pytest.approx(
        second_forward
    )

    # Simple finite-period forward differs slightly from the
    # continuously compounded instantaneous forward, so we do not
    # compare their numerical levels directly here.
    assert (
        segment.instantaneous_forward_rate
        > 0
    )


def test_identical_segment_slopes_produce_zero_jump() -> None:
    # Build discount factors from one constant continuously
    # compounded rate so both segments have identical log-DF slope.
    rate = 0.07

    first_date = date(
        2026,
        7,
        1,
    )

    second_date = date(
        2027,
        1,
        1,
    )

    first_time = (
        first_date
        - REFERENCE_DATE
    ).days / 360

    second_time = (
        second_date
        - REFERENCE_DATE
    ).days / 360

    from math import exp

    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            first_date,
            second_date,
        ),
        discount_factors=(
            exp(
                -rate
                * first_time
            ),
            exp(
                -rate
                * second_time
            ),
        ),
    )

    diagnostics = (
        calculate_log_linear_forward_diagnostics(
            curve
        )
    )

    assert len(
        diagnostics.jumps
    ) == 1

    assert (
        diagnostics.jumps[0].jump_bp
        == pytest.approx(
            0.0,
            abs=1e-10,
        )
    )


def test_different_segment_slopes_produce_forward_jump() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2026, 7, 1),
            date(2027, 1, 1),
        ),
        discount_factors=(
            0.97,
            0.92,
        ),
    )

    diagnostics = (
        calculate_log_linear_forward_diagnostics(
            curve
        )
    )

    assert len(
        diagnostics.jumps
    ) == 1

    assert abs(
        diagnostics.jumps[0].jump_bp
    ) > 0


def test_analyze_log_linear_curve_includes_method_diagnostics() -> None:
    curve = LogLinearDiscountCurve(
        reference_date=REFERENCE_DATE,
        node_dates=(
            date(2027, 1, 1),
            date(2028, 1, 1),
        ),
        discount_factors=(
            0.93,
            0.86,
        ),
    )

    report = analyze_curve(
        curve=curve,
        last_supported_date=(
            curve.last_node_date
        ),
        forward_period_days=28,
        grid_step_days=7,
    )

    assert (
        report.log_linear
        is not None
    )

    assert len(
        report.log_linear.segments
    ) == 2

    assert len(
        report.log_linear.jumps
    ) == 1


def test_generic_flat_curve_has_no_log_linear_specific_diagnostics() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        rate=0.07,
    )

    last_date = date(
        2027,
        1,
        1,
    )

    report = analyze_curve(
        curve=curve,
        last_supported_date=last_date,
        forward_period_days=28,
        grid_step_days=7,
    )

    assert (
        report.log_linear
        is None
    )


def test_flat_curve_sampled_forward_is_stable() -> None:
    curve = FlatContinuousZeroCurve(
        reference_date=REFERENCE_DATE,
        rate=0.07,
    )

    report = analyze_curve(
        curve=curve,
        last_supported_date=date(
            2027,
            1,
            1,
        ),
        forward_period_days=28,
        grid_step_days=7,
    )

    # A flat continuously compounded zero curve implies the same
    # simple forward for equal-length ACT/360 windows.
    assert (
        report.forward_summary
        .standard_deviation
        == pytest.approx(
            0.0,
            abs=1e-12,
        )
    )