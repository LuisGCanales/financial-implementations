"""Known-truth curve model for synthetic experiments."""

from dataclasses import dataclass
from datetime import date
from math import exp, isfinite
from ..conventions import act_360

@dataclass(frozen=True, slots=True)
class SmoothSyntheticZeroCurve:
    """Smooth parametric continuously compounded zero curve.

    This curve is used exclusively as the known-truth generator for
    synthetic calibration experiments.

    Zero rates are defined by:

        z(t)
        =
        L
        + S * exp(-t / tau_s)
        + H * t * exp(-t / tau_h)

    where:

        L
            Long-run zero-rate level.

        S
            Short-end spread over the long-run level.

        tau_s
            Decay parameter controlling the short-end component.

        H
            Curvature parameter.

        tau_h
            Decay parameter controlling the medium-term curvature.

    Discount factors are then:

        P(T0, T)
        =
        exp(-z(t) * t)

    with ACT/360 used as the synthetic time metric.

    Important
    ---------
    This is a PROJECT SYNTHETIC CURVE.

    It is not intended to represent observed MXN market data,
    CME methodology, or a market forecast.
    """

    reference_date: date

    long_run_rate: float
    short_spread: float
    short_decay_years: float

    curvature: float
    curvature_decay_years: float

    def __post_init__(self) -> None:
        parameters = (
            self.long_run_rate,
            self.short_spread,
            self.short_decay_years,
            self.curvature,
            self.curvature_decay_years,
        )

        if not all(
            isfinite(value)
            for value in parameters
        ):
            raise ValueError(
                "Synthetic curve parameters must be finite."
            )

        if self.short_decay_years <= 0:
            raise ValueError(
                "Short decay parameter must be positive."
            )

        if self.curvature_decay_years <= 0:
            raise ValueError(
                "Curvature decay parameter must be positive."
            )

    def _time(
        self,
        target_date: date,
    ) -> float:
        """Return ACT/360 time from reference date."""

        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede curve reference date."
            )

        return act_360(
            self.reference_date,
            target_date,
        )

    def zero_rate(
        self,
        target_date: date,
    ) -> float:
        """Return synthetic continuously compounded zero rate."""

        t = self._time(
            target_date
        )

        return (
            self.long_run_rate
            + self.short_spread
            * exp(
                -t / self.short_decay_years
            )
            + self.curvature
            * t
            * exp(
                -t / self.curvature_decay_years
            )
        )

    def discount_factor(
        self,
        target_date: date,
    ) -> float:
        """Return discount factor implied by synthetic zero curve."""

        t = self._time(
            target_date
        )

        zero = self.zero_rate(
            target_date
        )

        df = exp(
            -zero * t
        )

        if not isfinite(df) or df <= 0:
            raise ValueError(
                "Synthetic curve produced invalid discount factor."
            )

        return df

    def forward_rate(
        self,
        start_date: date,
        end_date: date,
    ) -> float:
        """Return simple ACT/360 forward implied by the curve."""

        if start_date < self.reference_date:
            raise ValueError(
                "Forward start cannot precede curve reference date."
            )

        if end_date <= start_date:
            raise ValueError(
                "Forward end must follow forward start."
            )

        p_start = self.discount_factor(
            start_date
        )

        p_end = self.discount_factor(
            end_date
        )

        tau = act_360(
            start_date,
            end_date,
        )

        return (
            p_start / p_end - 1.0
        ) / tau
        

