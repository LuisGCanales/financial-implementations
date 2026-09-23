"""Curve representations used by valuation and calibration.

The first curve implemented here is intentionally analytical rather
than calibrated.

Its purpose is to provide a known mathematical truth against which
instrument pricing and, later, calibration can be tested.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from math import exp, isfinite, log
from typing import Protocol, runtime_checkable

from .conventions import act_360


@runtime_checkable
class DiscountFactorCurve(Protocol):
    """Minimal curve interface required by pricing components.

    Both projection and discount curves expose discount-factor-like
    quantities.

    A projection curve may later represent pseudo-discount factors
    used to infer forward rates, while the discount curve represents
    actual present-value discounting.
    """

    reference_date: date

    def discount_factor(self, target_date: date) -> float:
        """Return curve discount factor at target date."""
        ...


@dataclass(frozen=True, slots=True)
class FlatContinuousZeroCurve:
    """Analytical flat continuously compounded zero curve.

    The curve is defined by:

        P(T0, T) = exp(-r * tau(T0, T))

    where tau uses ACT/360 in Core v1.

    This curve is not intended to represent a realistic market term
    structure. It is a deterministic known-truth object for testing
    pricing and calibration mechanics.
    """

    reference_date: date
    rate: float

    def __post_init__(self) -> None:
        if not isfinite(self.rate):
            raise ValueError(
                "Flat zero rate must be finite."
            )

    def discount_factor(
        self,
        target_date: date,
    ) -> float:
        """Return analytical discount factor."""

        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede curve reference date."
            )

        tau = act_360(
            self.reference_date,
            target_date,
        )

        return exp(
            -self.rate * tau
        )

    def zero_rate(
        self,
        target_date: date,
    ) -> float:
        """Return continuously compounded zero rate."""

        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede curve reference date."
            )

        return self.rate

    def forward_rate(
        self,
        start_date: date,
        end_date: date,
    ) -> float:
        """Return simple ACT/360 forward rate.

        F(T0; T1, T2)
        =
        [P(T0,T1) / P(T0,T2) - 1]
        /
        tau(T1,T2)
        """

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
        

@dataclass(frozen=True, slots=True)
class LogLinearDiscountCurve:
    """Nodal discount-factor curve with log-linear interpolation.

    State variable
    --------------
    Discount factors.

    Interpolation
    -------------
    Piecewise linear interpolation in:

        ln P(T)

    between the curve reference date and calibrated node dates.

    The curve does not extrapolate beyond its final node.
    """

    reference_date: date

    node_dates: tuple[date, ...]
    discount_factors: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.node_dates) != len(
            self.discount_factors
        ):
            raise ValueError(
                "Node dates and discount factors must "
                "have equal length."
            )

        if not self.node_dates:
            raise ValueError(
                "Curve must contain at least one node."
            )

        previous_date = self.reference_date

        for node_date in self.node_dates:
            if node_date <= previous_date:
                raise ValueError(
                    "Curve node dates must be strictly increasing "
                    "and follow the reference date."
                )

            previous_date = node_date

        for discount_factor in self.discount_factors:
            if (
                not isfinite(discount_factor)
                or discount_factor <= 0
            ):
                raise ValueError(
                    "Discount factors must be finite and positive."
                )

    @property
    def last_node_date(self) -> date:
        """Return final supported curve date."""

        return self.node_dates[-1]

    def discount_factor(
        self,
        target_date: date,
    ) -> float:
        """Return discount factor using log-linear interpolation."""

        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede curve reference date."
            )

        if target_date == self.reference_date:
            return 1.0

        if target_date > self.last_node_date:
            raise ValueError(
                "OUT_OF_CURVE_RANGE: "
                f"{target_date.isoformat()} exceeds "
                f"{self.last_node_date.isoformat()}."
            )

        index = bisect_left(
            self.node_dates,
            target_date,
        )

        # Exact calibrated node.
        if (
            index < len(self.node_dates)
            and self.node_dates[index] == target_date
        ):
            return self.discount_factors[index]

        if index == 0:
            left_date = self.reference_date
            left_df = 1.0
        else:
            left_date = self.node_dates[
                index - 1
            ]
            left_df = self.discount_factors[
                index - 1
            ]

        right_date = self.node_dates[index]
        right_df = self.discount_factors[index]

        t_left = act_360(
            self.reference_date,
            left_date,
        )

        t_right = act_360(
            self.reference_date,
            right_date,
        )

        t_target = act_360(
            self.reference_date,
            target_date,
        )

        weight = (
            (t_target - t_left)
            / (t_right - t_left)
        )

        log_left = log(left_df)
        log_right = log(right_df)

        interpolated_log_df = (
            log_left
            + weight
            * (log_right - log_left)
        )

        return exp(
            interpolated_log_df
        )

    def zero_rate(
        self,
        target_date: date,
    ) -> float:
        """Return continuously compounded ACT/360 zero rate."""

        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede curve reference date."
            )

        if target_date == self.reference_date:
            first_date = self.node_dates[0]
            first_df = self.discount_factors[0]

            tau = act_360(
                self.reference_date,
                first_date,
            )

            return (
                -log(first_df)
                / tau
            )

        df = self.discount_factor(
            target_date
        )

        tau = act_360(
            self.reference_date,
            target_date,
        )

        return (
            -log(df)
            / tau
        )

    def forward_rate(
        self,
        start_date: date,
        end_date: date,
    ) -> float:
        """Return simple ACT/360 forward rate."""

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
        
        

class CurveInterpolationMethod(StrEnum):
    """Supported nodal curve interpolation methods."""

    LOG_LINEAR_DF = "LOG_LINEAR_DF"
    LINEAR_CONTINUOUS_ZERO = "LINEAR_CONTINUOUS_ZERO"
    

@dataclass(frozen=True, slots=True)
class LinearContinuousZeroCurve:
    """Nodal curve with linear interpolation in continuous zero rates.

    The supplied state variables remain node discount factors.

    For each node:

        z_i = -ln(P_i) / t_i

    where t_i is ACT/360 time from the reference date.

    Between adjacent nodes, continuously compounded zero rates are
    interpolated linearly:

        z(t)
        =
        (1-w) z_i
        +
        w z_{i+1}

    and discount factors are reconstructed as:

        P(t) = exp(-z(t) t)

    First segment
    -------------
    Between the reference date and the first calibrated node, the
    first-node zero rate is held constant.

    This is an explicit project convention required because a zero
    rate at t=0 is not independently observable from the nodal input.

    Extrapolation beyond the final node is not permitted.
    """

    reference_date: date
    node_dates: tuple[date, ...]
    discount_factors: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.node_dates:
            raise ValueError(
                "At least one curve node is required."
            )

        if (
            len(self.node_dates)
            != len(self.discount_factors)
        ):
            raise ValueError(
                "Node dates and discount factors "
                "must have equal length."
            )

        previous_date = self.reference_date

        for node_date, discount_factor in zip(
            self.node_dates,
            self.discount_factors,
        ):
            if node_date <= previous_date:
                raise ValueError(
                    "Curve node dates must be strictly "
                    "increasing and later than the "
                    "reference date."
                )

            if (
                not isfinite(discount_factor)
                or discount_factor <= 0.0
            ):
                raise ValueError(
                    "Discount factors must be finite "
                    "and strictly positive."
                )

            previous_date = node_date

    @property
    def last_node_date(self) -> date:
        return self.node_dates[-1]

    @property
    def node_times(self) -> tuple[float, ...]:
        return tuple(
            (
                node_date
                - self.reference_date
            ).days
            / 360.0
            for node_date in self.node_dates
        )

    @property
    def node_zero_rates(self) -> tuple[float, ...]:
        return tuple(
            -log(discount_factor)
            / time
            for discount_factor, time in zip(
                self.discount_factors,
                self.node_times,
            )
        )

    def _time(
        self,
        target_date: date,
    ) -> float:
        return (
            target_date
            - self.reference_date
        ).days / 360.0

    def _interpolated_zero_rate(
        self,
        target_date: date,
    ) -> float:
        if target_date < self.reference_date:
            raise ValueError(
                "Target date cannot precede "
                "curve reference date."
            )

        if target_date > self.last_node_date:
            raise ValueError(
                "OUT_OF_CURVE_RANGE"
            )

        node_times = self.node_times
        zero_rates = self.node_zero_rates

        target_time = self._time(
            target_date
        )

        # Explicit reference-date / first-segment convention.
        if target_time <= node_times[0]:
            return zero_rates[0]

        index = bisect_right(
            self.node_dates,
            target_date,
        )

        # Exact final node.
        if index >= len(
            self.node_dates
        ):
            return zero_rates[-1]

        left_index = index - 1
        right_index = index

        left_time = node_times[
            left_index
        ]

        right_time = node_times[
            right_index
        ]

        left_zero = zero_rates[
            left_index
        ]

        right_zero = zero_rates[
            right_index
        ]

        weight = (
            target_time
            - left_time
        ) / (
            right_time
            - left_time
        )

        return (
            (1.0 - weight)
            * left_zero
            + weight
            * right_zero
        )

    def discount_factor(
        self,
        target_date: date,
    ) -> float:
        if target_date == self.reference_date:
            return 1.0

        zero_rate = (
            self._interpolated_zero_rate(
                target_date
            )
        )

        time = self._time(
            target_date
        )

        return exp(
            -zero_rate
            * time
        )

    def zero_rate(
        self,
        target_date: date,
    ) -> float:
        return (
            self._interpolated_zero_rate(
                target_date
            )
        )

    def forward_rate(
        self,
        start_date: date,
        end_date: date,
    ) -> float:
        if end_date <= start_date:
            raise ValueError(
                "Forward end date must follow "
                "forward start date."
            )

        if start_date < self.reference_date:
            raise ValueError(
                "Forward start date cannot precede "
                "curve reference date."
            )

        if end_date > self.last_node_date:
            raise ValueError(
                "OUT_OF_CURVE_RANGE"
            )

        start_df = self.discount_factor(
            start_date
        )

        end_df = self.discount_factor(
            end_date
        )

        accrual = (
            end_date
            - start_date
        ).days / 360.0

        return (
            start_df
            / end_df
            - 1.0
        ) / accrual
        

NodalCurve = (
    LogLinearDiscountCurve
    | LinearContinuousZeroCurve
)        


def build_nodal_curve(
    *,
    method: CurveInterpolationMethod,
    reference_date: date,
    node_dates: tuple[date, ...],
    discount_factors: tuple[float, ...],
) -> NodalCurve:
    """Build one supported nodal curve representation."""

    if (
        method
        == CurveInterpolationMethod.LOG_LINEAR_DF
    ):
        return LogLinearDiscountCurve(
            reference_date=(
                reference_date
            ),
            node_dates=node_dates,
            discount_factors=(
                discount_factors
            ),
        )

    if (
        method
        == CurveInterpolationMethod
        .LINEAR_CONTINUOUS_ZERO
    ):
        return LinearContinuousZeroCurve(
            reference_date=(
                reference_date
            ),
            node_dates=node_dates,
            discount_factors=(
                discount_factors
            ),
        )

    raise ValueError(
        "Unsupported interpolation method: "
        f"{method}"
    )