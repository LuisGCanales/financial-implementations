"""Exact segment and forward-jump calculations for log-linear curves."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import log

from .conventions import act_360
from .curves import LogLinearDiscountCurve

@dataclass(frozen=True, slots=True)
class LogLinearSegment:
    """One exact log-linear discount-factor segment.

    Within this segment:

        ln P(t)

    is linear in time.

    Therefore the continuously compounded instantaneous forward rate
    is constant inside the segment.
    """

    segment_number: int

    start_date: date
    end_date: date

    start_discount_factor: float
    end_discount_factor: float

    start_time: float
    end_time: float

    instantaneous_forward_rate: float


@dataclass(frozen=True, slots=True)
class ForwardJump:
    """Jump in segment-implied instantaneous forward at one pillar."""

    pillar_date: date

    left_segment_number: int
    right_segment_number: int

    left_forward_rate: float
    right_forward_rate: float

    jump_rate: float
    jump_bp: float


@dataclass(frozen=True, slots=True)
class LogLinearForwardDiagnostics:
    """Exact forward diagnostics for a log-linear DF curve."""

    segments: tuple[
        LogLinearSegment,
        ...
    ]

    jumps: tuple[
        ForwardJump,
        ...
    ]

    maximum_absolute_jump_bp: float
    maximum_absolute_jump_date: date | None

    mean_absolute_jump_bp: float


def calculate_log_linear_segments(
    curve: LogLinearDiscountCurve,
) -> tuple[
    LogLinearSegment,
    ...
]:
    """Calculate exact instantaneous-forward level in each segment.

    For a log-linear discount-factor segment:

        ln P(t) = a + b t

    the instantaneous forward is:

        f(t)
        =
        -d ln P(t) / dt
        =
        -b

    and is constant throughout the segment.
    """

    segments: list[
        LogLinearSegment
    ] = []

    previous_date = (
        curve.reference_date
    )

    previous_df = 1.0

    for index, (
        node_date,
        node_df,
    ) in enumerate(
        zip(
            curve.node_dates,
            curve.discount_factors,
        ),
        start=1,
    ):
        start_time = act_360(
            curve.reference_date,
            previous_date,
        )

        end_time = act_360(
            curve.reference_date,
            node_date,
        )

        delta_time = (
            end_time
            - start_time
        )

        if delta_time <= 0:
            raise ValueError(
                "Curve segment must have positive length."
            )

        slope_log_df = (
            log(node_df)
            - log(previous_df)
        ) / delta_time

        instantaneous_forward = (
            -slope_log_df
        )

        segments.append(
            LogLinearSegment(
                segment_number=index,
                start_date=previous_date,
                end_date=node_date,
                start_discount_factor=(
                    previous_df
                ),
                end_discount_factor=node_df,
                start_time=start_time,
                end_time=end_time,
                instantaneous_forward_rate=(
                    instantaneous_forward
                ),
            )
        )

        previous_date = node_date
        previous_df = node_df

    return tuple(
        segments
    )


def calculate_log_linear_forward_diagnostics(
    curve: LogLinearDiscountCurve,
) -> LogLinearForwardDiagnostics:
    """Calculate exact segment-forward jumps at calibrated pillars."""

    segments = (
        calculate_log_linear_segments(
            curve
        )
    )

    jumps: list[
        ForwardJump
    ] = []

    for left, right in zip(
        segments,
        segments[1:],
    ):
        if left.end_date != right.start_date:
            raise RuntimeError(
                "Adjacent curve segments are not contiguous."
            )

        jump_rate = (
            right.instantaneous_forward_rate
            - left.instantaneous_forward_rate
        )

        jumps.append(
            ForwardJump(
                pillar_date=left.end_date,
                left_segment_number=(
                    left.segment_number
                ),
                right_segment_number=(
                    right.segment_number
                ),
                left_forward_rate=(
                    left.instantaneous_forward_rate
                ),
                right_forward_rate=(
                    right.instantaneous_forward_rate
                ),
                jump_rate=jump_rate,
                jump_bp=(
                    jump_rate
                    * 10_000.0
                ),
            )
        )

    if jumps:
        largest = max(
            jumps,
            key=lambda jump: abs(
                jump.jump_bp
            ),
        )

        maximum_absolute_jump_bp = abs(
            largest.jump_bp
        )

        maximum_absolute_jump_date = (
            largest.pillar_date
        )

        mean_absolute_jump_bp = (
            sum(
                abs(
                    jump.jump_bp
                )
                for jump in jumps
            )
            / len(jumps)
        )

    else:
        maximum_absolute_jump_bp = 0.0
        maximum_absolute_jump_date = None
        mean_absolute_jump_bp = 0.0

    return LogLinearForwardDiagnostics(
        segments=segments,
        jumps=tuple(
            jumps
        ),
        maximum_absolute_jump_bp=(
            maximum_absolute_jump_bp
        ),
        maximum_absolute_jump_date=(
            maximum_absolute_jump_date
        ),
        mean_absolute_jump_bp=(
            mean_absolute_jump_bp
        ),
    )


