"""Recovery diagnostics for synthetic known-truth experiments.

This module evaluates how closely a calibrated curve recovers a curve
whose true structure is known.

Recovery diagnostics are distinct from calibration diagnostics.

Calibration asks:

    Does the recovered curve reproduce the quoted instruments?

Recovery asks:

    Does the recovered curve reproduce the latent curve that generated
    those quotes?

The second question is available only in controlled synthetic experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum, sqrt
from typing import Protocol, Sequence, runtime_checkable


@runtime_checkable
class RecoveryCurve(Protocol):
    """Curve interface required by recovery diagnostics."""

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
class ErrorSummary:
    """Summary statistics for one recovery-error series."""

    observation_count: int

    bias: float
    mae: float
    rmse: float

    max_abs_error: float
    max_abs_error_date: date


@dataclass(frozen=True, slots=True)
class RecoveryMetrics:
    """Complete synthetic curve-recovery diagnostics."""

    pillar_df_absolute: ErrorSummary
    pillar_df_relative_ppm: ErrorSummary

    dense_df_absolute: ErrorSummary
    dense_df_relative_ppm: ErrorSummary

    zero_rate_bp: ErrorSummary

    forward_28d_bp: ErrorSummary

    dense_grid_step_days: int
    forward_period_days: int


def _summarize_errors(
    *,
    dates: Sequence[date],
    errors: Sequence[float],
) -> ErrorSummary:
    """Return bias, MAE, RMSE, and maximum absolute error."""

    if len(dates) != len(errors):
        raise ValueError(
            "Dates and errors must have equal length."
        )

    if not errors:
        raise ValueError(
            "At least one error observation is required."
        )

    count = len(errors)

    bias = (
        fsum(errors)
        / count
    )

    absolute_errors = [
        abs(error)
        for error in errors
    ]

    mae = (
        fsum(absolute_errors)
        / count
    )

    squared_errors = [
        error * error
        for error in errors
    ]

    rmse = sqrt(
        fsum(squared_errors)
        / count
    )

    max_index = max(
        range(count),
        key=lambda index: absolute_errors[index],
    )

    return ErrorSummary(
        observation_count=count,
        bias=bias,
        mae=mae,
        rmse=rmse,
        max_abs_error=absolute_errors[max_index],
        max_abs_error_date=dates[max_index],
    )


def _build_date_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int,
) -> tuple[date, ...]:
    """Build deterministic date grid including the final date."""

    if step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    if end_date < start_date:
        raise ValueError(
            "End date cannot precede start date."
        )

    dates: list[date] = []

    current = start_date

    while current < end_date:
        dates.append(current)
        current += timedelta(
            days=step_days
        )

    if not dates or dates[-1] != end_date:
        dates.append(end_date)

    return tuple(dates)


def calculate_recovery_metrics(
    *,
    true_curve: RecoveryCurve,
    recovered_curve: RecoveryCurve,
    pillar_dates: Sequence[date],
    last_supported_date: date,
    dense_grid_step_days: int = 7,
    forward_period_days: int = 28,
) -> RecoveryMetrics:
    """Calculate synthetic curve-recovery metrics.

    Parameters
    ----------
    true_curve
        Known curve that generated the synthetic market quotes.

    recovered_curve
        Curve calibrated only from those synthetic quotes.

    pillar_dates
        Calibration pillar dates.

    last_supported_date
        Final date supported by the recovered curve.

    dense_grid_step_days
        Spacing used for dense recovery comparison.

    forward_period_days
        Horizon of the simple forward-rate comparison.

    Notes
    -----
    Discount-factor errors are reported both as:

        recovered DF - true DF

    and relative error:

        (recovered DF / true DF - 1) * 1_000_000

    where the latter is expressed in parts per million.

    Zero-rate and forward-rate errors are expressed in basis points.
    """

    if (
        true_curve.reference_date
        != recovered_curve.reference_date
    ):
        raise ValueError(
            "True and recovered curves must share "
            "the same reference date."
        )

    reference_date = (
        recovered_curve.reference_date
    )

    if last_supported_date <= reference_date:
        raise ValueError(
            "Last supported date must follow reference date."
        )

    if not pillar_dates:
        raise ValueError(
            "At least one calibration pillar is required."
        )

    # ------------------------------------------------------------------
    # Pillar discount-factor recovery
    # ------------------------------------------------------------------

    pillar_df_errors: list[float] = []
    pillar_relative_errors_ppm: list[float] = []

    for pillar_date in pillar_dates:
        true_df = (
            true_curve.discount_factor(
                pillar_date
            )
        )

        recovered_df = (
            recovered_curve.discount_factor(
                pillar_date
            )
        )

        absolute_error = (
            recovered_df
            - true_df
        )

        relative_error_ppm = (
            recovered_df
            / true_df
            - 1.0
        ) * 1_000_000.0

        pillar_df_errors.append(
            absolute_error
        )

        pillar_relative_errors_ppm.append(
            relative_error_ppm
        )

    # ------------------------------------------------------------------
    # Dense discount-factor and zero-rate recovery
    # ------------------------------------------------------------------

    dense_dates = _build_date_grid(
        start_date=reference_date,
        end_date=last_supported_date,
        step_days=dense_grid_step_days,
    )

    dense_df_errors: list[float] = []
    dense_relative_errors_ppm: list[float] = []

    for target_date in dense_dates:
        true_df = (
            true_curve.discount_factor(
                target_date
            )
        )

        recovered_df = (
            recovered_curve.discount_factor(
                target_date
            )
        )

        dense_df_errors.append(
            recovered_df
            - true_df
        )

        dense_relative_errors_ppm.append(
            (
                recovered_df
                / true_df
                - 1.0
            )
            * 1_000_000.0
        )

    # Zero-rate comparison starts after reference date because t = 0
    # is not a meaningful finite-maturity recovery observation.
    zero_dates = tuple(
        target_date
        for target_date in dense_dates
        if target_date > reference_date
    )

    zero_errors_bp: list[float] = []

    for target_date in zero_dates:
        true_zero = (
            true_curve.zero_rate(
                target_date
            )
        )

        recovered_zero = (
            recovered_curve.zero_rate(
                target_date
            )
        )

        zero_errors_bp.append(
            (
                recovered_zero
                - true_zero
            )
            * 10_000.0
        )

    # ------------------------------------------------------------------
    # 28-day forward-rate recovery
    # ------------------------------------------------------------------

    last_forward_start = (
        last_supported_date
        - timedelta(
            days=forward_period_days
        )
    )

    if last_forward_start < reference_date:
        raise ValueError(
            "Curve horizon is too short for requested "
            "forward-period comparison."
        )

    forward_start_dates = (
        _build_date_grid(
            start_date=reference_date,
            end_date=last_forward_start,
            step_days=dense_grid_step_days,
        )
    )

    forward_errors_bp: list[float] = []

    for start_date in forward_start_dates:
        end_date = (
            start_date
            + timedelta(
                days=forward_period_days
            )
        )

        true_forward = (
            true_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        recovered_forward = (
            recovered_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        forward_errors_bp.append(
            (
                recovered_forward
                - true_forward
            )
            * 10_000.0
        )

    return RecoveryMetrics(
        pillar_df_absolute=_summarize_errors(
            dates=pillar_dates,
            errors=pillar_df_errors,
        ),
        pillar_df_relative_ppm=_summarize_errors(
            dates=pillar_dates,
            errors=pillar_relative_errors_ppm,
        ),
        dense_df_absolute=_summarize_errors(
            dates=dense_dates,
            errors=dense_df_errors,
        ),
        dense_df_relative_ppm=_summarize_errors(
            dates=dense_dates,
            errors=dense_relative_errors_ppm,
        ),
        zero_rate_bp=_summarize_errors(
            dates=zero_dates,
            errors=zero_errors_bp,
        ),
        forward_28d_bp=_summarize_errors(
            dates=forward_start_dates,
            errors=forward_errors_bp,
        ),
        dense_grid_step_days=dense_grid_step_days,
        forward_period_days=forward_period_days,
    )