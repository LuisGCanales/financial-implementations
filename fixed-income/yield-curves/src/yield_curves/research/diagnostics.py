"""Historical combined curve diagnostic report orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..curves import LogLinearDiscountCurve
from ..diagnostics import (DiagnosticCurve, ForwardObservation, ForwardCurveSummary, build_forward_observations, summarize_forward_observations)
from ..log_linear_diagnostics import (LogLinearForwardDiagnostics, calculate_log_linear_forward_diagnostics)

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

