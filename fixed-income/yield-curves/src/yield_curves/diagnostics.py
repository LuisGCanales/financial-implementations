"""Reusable forward sampling and summaries; no acceptance policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import isfinite, sqrt
from typing import Protocol, Sequence, runtime_checkable

from .conventions import act_360
from .date_grids import iter_forward_start_dates

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

    for start_date in iter_forward_start_dates(
        reference_date=reference_date,
        last_start_date=last_start_date,
        grid_step_days=grid_step_days,
    ):
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


