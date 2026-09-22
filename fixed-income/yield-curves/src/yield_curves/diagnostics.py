"""Curve-shape and forward-rate diagnostics.

These diagnostics inspect the financial behavior of a calibrated curve.

They are deliberately separate from:

- calibration;
- independent repricing;
- synthetic recovery analysis.

A curve can reprice all calibration instruments and still display
methodology-induced behavior that deserves inspection.

The diagnostics in this module do not automatically imply that a curve
is invalid.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite, log, sqrt
from typing import Protocol, Sequence, runtime_checkable

from .conventions import act_360
from .curves import LogLinearDiscountCurve


@runtime_checkable
class DiagnosticCurve(Protocol):
    """Minimal interface required by generic curve diagnostics."""

    reference_date: date

    def discount_factor(
        self,
        target_date: date,
    ) -> float:
        ...

    def zero_rate(
        self,
        target_date: date,
    ) -> float:
        ...

    def forward_rate(
        self,
        start_date: date,
        end_date: date,
    ) -> float:
        ...


@dataclass(frozen=True, slots=True)
class ForwardObservation:
    """One sampled simple-forward observation."""

    start_date: date
    end_date: date

    start_time: float
    end_time: float

    rate: float


@dataclass(frozen=True, slots=True)
class ForwardCurveSummary:
    """Summary statistics for a sampled forward curve."""

    observation_count: int

    minimum_rate: float
    minimum_rate_date: date

    maximum_rate: float
    maximum_rate_date: date

    mean_rate: float
    standard_deviation: float

    maximum_local_change_bp: float
    maximum_local_change_date: date


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


@dataclass(frozen=True, slots=True)
class CurveDiagnosticsReport:
    """Combined generic and methodology-specific diagnostics."""

    sampled_forwards: tuple[
        ForwardObservation,
        ...
    ]

    forward_summary: ForwardCurveSummary

    log_linear: LogLinearForwardDiagnostics | None

    forward_period_days: int
    grid_step_days: int


def build_forward_observations(
    *,
    curve: DiagnosticCurve,
    last_supported_date: date,
    forward_period_days: int = 28,
    grid_step_days: int = 7,
) -> tuple[
    ForwardObservation,
    ...
]:
    """Sample simple forward rates across the curve domain."""

    if forward_period_days <= 0:
        raise ValueError(
            "Forward period must be positive."
        )

    if grid_step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    reference_date = curve.reference_date

    last_start_date = (
        last_supported_date
        - timedelta(
            days=forward_period_days
        )
    )

    if last_start_date < reference_date:
        raise ValueError(
            "Curve horizon is too short for requested "
            "forward period."
        )

    observations: list[
        ForwardObservation
    ] = []

    start_date = reference_date

    while start_date <= last_start_date:
        end_date = (
            start_date
            + timedelta(
                days=forward_period_days
            )
        )

        rate = curve.forward_rate(
            start_date,
            end_date,
        )

        if not isfinite(rate):
            raise ValueError(
                "Curve produced non-finite forward rate."
            )

        observations.append(
            ForwardObservation(
                start_date=start_date,
                end_date=end_date,
                start_time=act_360(
                    reference_date,
                    start_date,
                ),
                end_time=act_360(
                    reference_date,
                    end_date,
                ),
                rate=rate,
            )
        )

        start_date += timedelta(
            days=grid_step_days
        )

    return tuple(
        observations
    )


def summarize_forward_observations(
    observations: Sequence[
        ForwardObservation
    ],
) -> ForwardCurveSummary:
    """Summarize sampled forward-curve behavior."""

    if not observations:
        raise ValueError(
            "At least one forward observation is required."
        )

    rates = [
        observation.rate
        for observation in observations
    ]

    minimum_index = min(
        range(len(rates)),
        key=lambda index: rates[index],
    )

    maximum_index = max(
        range(len(rates)),
        key=lambda index: rates[index],
    )

    mean_rate = (
        sum(rates)
        / len(rates)
    )

    variance = (
        sum(
            (
                rate
                - mean_rate
            )
            ** 2
            for rate in rates
        )
        / len(rates)
    )

    standard_deviation = sqrt(
        variance
    )

    if len(observations) == 1:
        maximum_local_change_bp = 0.0
        maximum_local_change_date = (
            observations[0].start_date
        )

    else:
        local_changes_bp = [
            (
                observations[index].rate
                - observations[index - 1].rate
            )
            * 10_000.0
            for index in range(
                1,
                len(observations),
            )
        ]

        max_change_index = max(
            range(
                len(local_changes_bp)
            ),
            key=lambda index: abs(
                local_changes_bp[index]
            ),
        )

        maximum_local_change_bp = (
            local_changes_bp[
                max_change_index
            ]
        )

        maximum_local_change_date = (
            observations[
                max_change_index + 1
            ].start_date
        )

    return ForwardCurveSummary(
        observation_count=len(
            observations
        ),
        minimum_rate=rates[
            minimum_index
        ],
        minimum_rate_date=(
            observations[
                minimum_index
            ].start_date
        ),
        maximum_rate=rates[
            maximum_index
        ],
        maximum_rate_date=(
            observations[
                maximum_index
            ].start_date
        ),
        mean_rate=mean_rate,
        standard_deviation=(
            standard_deviation
        ),
        maximum_local_change_bp=(
            maximum_local_change_bp
        ),
        maximum_local_change_date=(
            maximum_local_change_date
        ),
    )


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


def analyze_curve(
    *,
    curve: DiagnosticCurve,
    last_supported_date: date,
    forward_period_days: int = 28,
    grid_step_days: int = 7,
) -> CurveDiagnosticsReport:
    """Run generic and available methodology-specific diagnostics."""

    sampled_forwards = (
        build_forward_observations(
            curve=curve,
            last_supported_date=(
                last_supported_date
            ),
            forward_period_days=(
                forward_period_days
            ),
            grid_step_days=(
                grid_step_days
            ),
        )
    )

    forward_summary = (
        summarize_forward_observations(
            sampled_forwards
        )
    )

    if isinstance(
        curve,
        LogLinearDiscountCurve,
    ):
        log_linear = (
            calculate_log_linear_forward_diagnostics(
                curve
            )
        )
    else:
        log_linear = None

    return CurveDiagnosticsReport(
        sampled_forwards=(
            sampled_forwards
        ),
        forward_summary=(
            forward_summary
        ),
        log_linear=log_linear,
        forward_period_days=(
            forward_period_days
        ),
        grid_step_days=(
            grid_step_days
        ),
    )