"""Quote-perturbation sensitivity diagnostics.

This module studies how a calibrated curve responds to small changes
in its market inputs.

The canonical experiment uses one-factor-at-a-time parallel-sized
quote shocks:

    quote_i -> quote_i + bump

while all other calibration quotes remain unchanged.

For a sequential bootstrap, a perturbation to quote i should not affect
already-solved nodes 1, ..., i-1. It may affect node i and all later
nodes because later instruments are calibrated conditional on the
previously solved curve.

These diagnostics measure:

- node discount-factor changes;
- node zero-rate changes;
- upstream invariance;
- 28-day forward-rate changes;
- local propagation of each quote shock.

They are descriptive diagnostics, not automatic validity thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum, sqrt
from typing import Sequence

from .bootstrap import (
    BootstrapResult,
    OISCalibrationQuote,
    bootstrap_ftiie_ois_curve,
)
from .calendars import BusinessCalendar


@dataclass(frozen=True, slots=True)
class PerturbedCalibrationQuote:
    """Minimal calibration quote used for one-factor perturbations."""

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float


@dataclass(frozen=True, slots=True)
class NodeSensitivity:
    """Response of one calibrated node to one quote perturbation."""

    shock_tenor: str
    node_tenor: str

    node_index: int
    node_date: date

    base_discount_factor: float
    shocked_discount_factor: float

    delta_discount_factor: float
    relative_df_change_ppm: float

    base_zero_rate: float
    shocked_zero_rate: float

    delta_zero_rate_bp: float
    zero_sensitivity_bp_per_bp: float

    is_upstream: bool
    is_shocked_node: bool
    is_downstream: bool


@dataclass(frozen=True, slots=True)
class ForwardSensitivitySummary:
    """Summary of 28-day forward changes under one quote shock."""

    observation_count: int

    bias_bp: float
    mae_bp: float
    rmse_bp: float

    max_abs_change_bp: float
    max_abs_change_date: date


@dataclass(frozen=True, slots=True)
class QuotePerturbationResult:
    """Curve response to one perturbed market quote."""

    shock_index: int
    shock_tenor: str

    bump_bp: float

    original_quote: float
    shocked_quote: float

    node_sensitivities: tuple[
        NodeSensitivity,
        ...
    ]

    forward_summary: ForwardSensitivitySummary

    maximum_upstream_abs_df_change: float
    upstream_invariance_pass: bool

    own_node_delta_df: float
    own_node_zero_change_bp: float


@dataclass(frozen=True, slots=True)
class QuotePerturbationReport:
    """Complete one-factor quote-perturbation experiment."""

    reference_date: date

    bump_bp: float
    forward_period_days: int
    grid_step_days: int

    upstream_df_tolerance: float

    base_result: BootstrapResult

    perturbations: tuple[
        QuotePerturbationResult,
        ...
    ]


def _build_perturbed_quotes(
    *,
    quotes: Sequence[OISCalibrationQuote],
    shock_index: int,
    bump_bp: float,
) -> tuple[
    PerturbedCalibrationQuote,
    ...
]:
    """Return quote set with exactly one par rate perturbed."""

    if not quotes:
        raise ValueError(
            "At least one quote is required."
        )

    if not (
        0 <= shock_index < len(quotes)
    ):
        raise IndexError(
            "Shock index is outside quote set."
        )

    bump_rate = (
        bump_bp
        / 10_000.0
    )

    perturbed: list[
        PerturbedCalibrationQuote
    ] = []

    for index, quote in enumerate(
        quotes
    ):
        par_rate = quote.par_rate

        if index == shock_index:
            par_rate += bump_rate

        perturbed.append(
            PerturbedCalibrationQuote(
                tenor=quote.tenor,
                trade_date=quote.trade_date,
                contractual_maturity_date=(
                    quote.contractual_maturity_date
                ),
                par_rate=par_rate,
            )
        )

    return tuple(
        perturbed
    )


def _build_forward_start_dates(
    *,
    reference_date: date,
    last_supported_date: date,
    forward_period_days: int,
    grid_step_days: int,
) -> tuple[date, ...]:
    """Build deterministic grid of forward start dates."""

    if forward_period_days <= 0:
        raise ValueError(
            "Forward period must be positive."
        )

    if grid_step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    last_start_date = (
        last_supported_date
        - timedelta(
            days=forward_period_days
        )
    )

    if last_start_date < reference_date:
        raise ValueError(
            "Curve horizon is too short for "
            "the requested forward period."
        )

    dates: list[date] = []

    current = reference_date

    while current <= last_start_date:
        dates.append(
            current
        )

        current += timedelta(
            days=grid_step_days
        )

    return tuple(
        dates
    )


def _summarize_forward_changes(
    *,
    base_curve,
    shocked_curve,
    forward_start_dates: Sequence[date],
    forward_period_days: int,
) -> ForwardSensitivitySummary:
    """Compare sampled forward curves after one quote perturbation."""

    changes_bp: list[float] = []

    for start_date in forward_start_dates:
        end_date = (
            start_date
            + timedelta(
                days=forward_period_days
            )
        )

        base_forward = (
            base_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        shocked_forward = (
            shocked_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        changes_bp.append(
            (
                shocked_forward
                - base_forward
            )
            * 10_000.0
        )

    if not changes_bp:
        raise ValueError(
            "No forward observations available."
        )

    observation_count = len(
        changes_bp
    )

    bias_bp = (
        fsum(
            changes_bp
        )
        / observation_count
    )

    absolute_changes = [
        abs(change)
        for change in changes_bp
    ]

    mae_bp = (
        fsum(
            absolute_changes
        )
        / observation_count
    )

    rmse_bp = sqrt(
        fsum(
            change * change
            for change in changes_bp
        )
        / observation_count
    )

    max_index = max(
        range(
            observation_count
        ),
        key=lambda index: (
            absolute_changes[index]
        ),
    )

    return ForwardSensitivitySummary(
        observation_count=(
            observation_count
        ),
        bias_bp=bias_bp,
        mae_bp=mae_bp,
        rmse_bp=rmse_bp,
        max_abs_change_bp=(
            absolute_changes[
                max_index
            ]
        ),
        max_abs_change_date=(
            forward_start_dates[
                max_index
            ]
        ),
    )


def _calculate_node_sensitivities(
    *,
    quotes: Sequence[OISCalibrationQuote],
    base_result: BootstrapResult,
    shocked_result: BootstrapResult,
    shock_index: int,
    bump_bp: float,
) -> tuple[
    NodeSensitivity,
    ...
]:
    """Compare calibrated nodes before and after one quote shock."""

    base_curve = (
        base_result.curve
    )

    shocked_curve = (
        shocked_result.curve
    )

    if (
        base_curve.reference_date
        != shocked_curve.reference_date
    ):
        raise ValueError(
            "Base and shocked curves have "
            "different reference dates."
        )

    if (
        base_curve.node_dates
        != shocked_curve.node_dates
    ):
        raise ValueError(
            "Base and shocked curves do not "
            "share identical node dates."
        )

    if (
        len(base_curve.node_dates)
        != len(quotes)
    ):
        raise ValueError(
            "Node count does not match quote count."
        )

    if bump_bp == 0:
        raise ValueError(
            "Quote bump cannot be zero."
        )

    sensitivities: list[
        NodeSensitivity
    ] = []

    for node_index, (
        quote,
        node_date,
        base_df,
        shocked_df,
    ) in enumerate(
        zip(
            quotes,
            base_curve.node_dates,
            base_curve.discount_factors,
            shocked_curve.discount_factors,
        )
    ):
        delta_df = (
            shocked_df
            - base_df
        )

        relative_df_change_ppm = (
            delta_df
            / base_df
            * 1_000_000.0
        )

        base_zero = (
            base_curve.zero_rate(
                node_date
            )
        )

        shocked_zero = (
            shocked_curve.zero_rate(
                node_date
            )
        )

        delta_zero_bp = (
            shocked_zero
            - base_zero
        ) * 10_000.0

        sensitivities.append(
            NodeSensitivity(
                shock_tenor=(
                    quotes[
                        shock_index
                    ].tenor
                ),
                node_tenor=(
                    quote.tenor
                ),
                node_index=node_index,
                node_date=node_date,
                base_discount_factor=(
                    base_df
                ),
                shocked_discount_factor=(
                    shocked_df
                ),
                delta_discount_factor=(
                    delta_df
                ),
                relative_df_change_ppm=(
                    relative_df_change_ppm
                ),
                base_zero_rate=(
                    base_zero
                ),
                shocked_zero_rate=(
                    shocked_zero
                ),
                delta_zero_rate_bp=(
                    delta_zero_bp
                ),
                zero_sensitivity_bp_per_bp=(
                    delta_zero_bp
                    / bump_bp
                ),
                is_upstream=(
                    node_index
                    < shock_index
                ),
                is_shocked_node=(
                    node_index
                    == shock_index
                ),
                is_downstream=(
                    node_index
                    > shock_index
                ),
            )
        )

    return tuple(
        sensitivities
    )


def analyze_quote_perturbations(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    bump_bp: float = 1.0,
    forward_period_days: int = 28,
    grid_step_days: int = 7,
    upstream_df_tolerance: float = 1e-12,
) -> QuotePerturbationReport:
    """Run one-factor-at-a-time quote perturbation analysis.

    Each calibration quote is increased by `bump_bp`, one at a time.

    A completely new bootstrap is performed after every perturbation.

    This deliberately tests the full calibration pipeline rather than
    applying an analytical approximation around the base curve.
    """

    if not quotes:
        raise ValueError(
            "At least one quote is required."
        )

    if bump_bp == 0:
        raise ValueError(
            "Quote bump cannot be zero."
        )

    if upstream_df_tolerance < 0:
        raise ValueError(
            "Upstream tolerance cannot be negative."
        )

    base_result = (
        bootstrap_ftiie_ois_curve(
            quotes=quotes,
            calendar=calendar,
        )
    )

    base_curve = (
        base_result.curve
    )

    forward_start_dates = (
        _build_forward_start_dates(
            reference_date=(
                base_curve.reference_date
            ),
            last_supported_date=(
                base_curve.last_node_date
            ),
            forward_period_days=(
                forward_period_days
            ),
            grid_step_days=(
                grid_step_days
            ),
        )
    )

    results: list[
        QuotePerturbationResult
    ] = []

    for shock_index, quote in enumerate(
        quotes
    ):
        shocked_quotes = (
            _build_perturbed_quotes(
                quotes=quotes,
                shock_index=shock_index,
                bump_bp=bump_bp,
            )
        )

        shocked_result = (
            bootstrap_ftiie_ois_curve(
                quotes=shocked_quotes,
                calendar=calendar,
            )
        )

        sensitivities = (
            _calculate_node_sensitivities(
                quotes=quotes,
                base_result=base_result,
                shocked_result=(
                    shocked_result
                ),
                shock_index=shock_index,
                bump_bp=bump_bp,
            )
        )

        upstream_changes = [
            abs(
                sensitivity
                .delta_discount_factor
            )
            for sensitivity
            in sensitivities
            if sensitivity.is_upstream
        ]

        if upstream_changes:
            maximum_upstream_change = max(
                upstream_changes
            )
        else:
            maximum_upstream_change = 0.0

        upstream_invariance_pass = (
            maximum_upstream_change
            <= upstream_df_tolerance
        )

        own_node = sensitivities[
            shock_index
        ]

        forward_summary = (
            _summarize_forward_changes(
                base_curve=base_curve,
                shocked_curve=(
                    shocked_result.curve
                ),
                forward_start_dates=(
                    forward_start_dates
                ),
                forward_period_days=(
                    forward_period_days
                ),
            )
        )

        results.append(
            QuotePerturbationResult(
                shock_index=shock_index,
                shock_tenor=quote.tenor,
                bump_bp=bump_bp,
                original_quote=(
                    quote.par_rate
                ),
                shocked_quote=(
                    quote.par_rate
                    + bump_bp
                    / 10_000.0
                ),
                node_sensitivities=(
                    sensitivities
                ),
                forward_summary=(
                    forward_summary
                ),
                maximum_upstream_abs_df_change=(
                    maximum_upstream_change
                ),
                upstream_invariance_pass=(
                    upstream_invariance_pass
                ),
                own_node_delta_df=(
                    own_node
                    .delta_discount_factor
                ),
                own_node_zero_change_bp=(
                    own_node
                    .delta_zero_rate_bp
                ),
            )
        )

    return QuotePerturbationReport(
        reference_date=(
            base_curve.reference_date
        ),
        bump_bp=bump_bp,
        forward_period_days=(
            forward_period_days
        ),
        grid_step_days=(
            grid_step_days
        ),
        upstream_df_tolerance=(
            upstream_df_tolerance
        ),
        base_result=base_result,
        perturbations=tuple(
            results
        ),
    )
    

@dataclass(frozen=True, slots=True)
class CentralNodeSensitivity:
    """Symmetric local sensitivity of one curve node."""

    shock_tenor: str
    node_tenor: str

    node_index: int
    node_date: date

    base_zero_rate: float
    plus_zero_rate: float
    minus_zero_rate: float

    plus_response_bp: float
    minus_response_bp: float

    central_sensitivity_bp_per_bp: float
    curvature_bp_per_bp2: float

    is_upstream: bool
    is_shocked_node: bool
    is_downstream: bool


@dataclass(frozen=True, slots=True)
class CentralForwardSensitivitySummary:
    """Symmetric sensitivity and curvature of sampled forwards."""

    observation_count: int

    sensitivity_bias: float
    sensitivity_mae: float
    sensitivity_rmse: float

    max_abs_sensitivity: float
    max_abs_sensitivity_date: date

    curvature_mae: float
    curvature_rmse: float

    max_abs_curvature: float
    max_abs_curvature_date: date


@dataclass(frozen=True, slots=True)
class CentralQuotePerturbationResult:
    """Symmetric perturbation diagnostics for one calibration quote."""

    shock_index: int
    shock_tenor: str

    bump_bp: float

    node_sensitivities: tuple[
        CentralNodeSensitivity,
        ...
    ]

    forward_summary: CentralForwardSensitivitySummary

    maximum_upstream_abs_sensitivity: float
    maximum_upstream_abs_curvature: float

    own_node_sensitivity: float
    own_node_curvature: float


@dataclass(frozen=True, slots=True)
class CentralQuotePerturbationReport:
    """Complete symmetric quote-perturbation experiment."""

    reference_date: date
    bump_bp: float

    forward_period_days: int
    grid_step_days: int

    base_result: BootstrapResult

    perturbations: tuple[
        CentralQuotePerturbationResult,
        ...
    ]


def _calculate_central_node_sensitivities(
    *,
    quotes: Sequence[OISCalibrationQuote],
    base_result: BootstrapResult,
    plus_result: BootstrapResult,
    minus_result: BootstrapResult,
    shock_index: int,
    bump_bp: float,
) -> tuple[CentralNodeSensitivity, ...]:
    """Calculate symmetric first- and second-order node responses."""

    if bump_bp <= 0:
        raise ValueError(
            "Central perturbation bump must be positive."
        )

    base_curve = base_result.curve
    plus_curve = plus_result.curve
    minus_curve = minus_result.curve

    if not (
        base_curve.node_dates
        == plus_curve.node_dates
        == minus_curve.node_dates
    ):
        raise ValueError(
            "Base, plus, and minus curves must share node dates."
        )

    sensitivities: list[
        CentralNodeSensitivity
    ] = []

    for node_index, (
        quote,
        node_date,
    ) in enumerate(
        zip(
            quotes,
            base_curve.node_dates,
        )
    ):
        base_zero = (
            base_curve.zero_rate(
                node_date
            )
        )

        plus_zero = (
            plus_curve.zero_rate(
                node_date
            )
        )

        minus_zero = (
            minus_curve.zero_rate(
                node_date
            )
        )

        # Directional responses are both expressed in the
        # +quote direction so they are directly comparable.
        plus_response_bp = (
            plus_zero
            - base_zero
        ) * 10_000.0

        minus_response_bp = (
            base_zero
            - minus_zero
        ) * 10_000.0

        central_sensitivity = (
            (
                plus_zero
                - minus_zero
            )
            * 10_000.0
            / (2.0 * bump_bp)
        )

        curvature = (
            (
                plus_zero
                - 2.0 * base_zero
                + minus_zero
            )
            * 10_000.0
            / (bump_bp ** 2)
        )

        sensitivities.append(
            CentralNodeSensitivity(
                shock_tenor=(
                    quotes[
                        shock_index
                    ].tenor
                ),
                node_tenor=quote.tenor,
                node_index=node_index,
                node_date=node_date,
                base_zero_rate=base_zero,
                plus_zero_rate=plus_zero,
                minus_zero_rate=minus_zero,
                plus_response_bp=(
                    plus_response_bp
                ),
                minus_response_bp=(
                    minus_response_bp
                ),
                central_sensitivity_bp_per_bp=(
                    central_sensitivity
                ),
                curvature_bp_per_bp2=(
                    curvature
                ),
                is_upstream=(
                    node_index
                    < shock_index
                ),
                is_shocked_node=(
                    node_index
                    == shock_index
                ),
                is_downstream=(
                    node_index
                    > shock_index
                ),
            )
        )

    return tuple(
        sensitivities
    )


def _summarize_central_forward_sensitivity(
    *,
    base_curve,
    plus_curve,
    minus_curve,
    forward_start_dates: Sequence[date],
    forward_period_days: int,
    bump_bp: float,
) -> CentralForwardSensitivitySummary:
    """Calculate symmetric forward sensitivity and curvature."""

    sensitivities: list[float] = []
    curvatures: list[float] = []

    for start_date in forward_start_dates:
        end_date = (
            start_date
            + timedelta(
                days=forward_period_days
            )
        )

        base_forward = (
            base_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        plus_forward = (
            plus_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        minus_forward = (
            minus_curve.forward_rate(
                start_date,
                end_date,
            )
        )

        central_sensitivity = (
            (
                plus_forward
                - minus_forward
            )
            * 10_000.0
            / (2.0 * bump_bp)
        )

        curvature = (
            (
                plus_forward
                - 2.0 * base_forward
                + minus_forward
            )
            * 10_000.0
            / (bump_bp ** 2)
        )

        sensitivities.append(
            central_sensitivity
        )

        curvatures.append(
            curvature
        )

    if not sensitivities:
        raise ValueError(
            "No forward observations available."
        )

    count = len(
        sensitivities
    )

    sensitivity_bias = (
        fsum(
            sensitivities
        )
        / count
    )

    sensitivity_mae = (
        fsum(
            abs(value)
            for value in sensitivities
        )
        / count
    )

    sensitivity_rmse = sqrt(
        fsum(
            value * value
            for value in sensitivities
        )
        / count
    )

    max_sensitivity_index = max(
        range(count),
        key=lambda index: abs(
            sensitivities[index]
        ),
    )

    curvature_mae = (
        fsum(
            abs(value)
            for value in curvatures
        )
        / count
    )

    curvature_rmse = sqrt(
        fsum(
            value * value
            for value in curvatures
        )
        / count
    )

    max_curvature_index = max(
        range(count),
        key=lambda index: abs(
            curvatures[index]
        ),
    )

    return CentralForwardSensitivitySummary(
        observation_count=count,
        sensitivity_bias=(
            sensitivity_bias
        ),
        sensitivity_mae=(
            sensitivity_mae
        ),
        sensitivity_rmse=(
            sensitivity_rmse
        ),
        max_abs_sensitivity=abs(
            sensitivities[
                max_sensitivity_index
            ]
        ),
        max_abs_sensitivity_date=(
            forward_start_dates[
                max_sensitivity_index
            ]
        ),
        curvature_mae=(
            curvature_mae
        ),
        curvature_rmse=(
            curvature_rmse
        ),
        max_abs_curvature=abs(
            curvatures[
                max_curvature_index
            ]
        ),
        max_abs_curvature_date=(
            forward_start_dates[
                max_curvature_index
            ]
        ),
    )


def analyze_central_quote_perturbations(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    bump_bp: float = 1.0,
    forward_period_days: int = 28,
    grid_step_days: int = 7,
) -> CentralQuotePerturbationReport:
    """Run symmetric +bump/-bump quote perturbation diagnostics."""

    if not quotes:
        raise ValueError(
            "At least one quote is required."
        )

    if bump_bp <= 0:
        raise ValueError(
            "Central perturbation bump must be positive."
        )

    base_result = (
        bootstrap_ftiie_ois_curve(
            quotes=quotes,
            calendar=calendar,
        )
    )

    base_curve = (
        base_result.curve
    )

    forward_start_dates = (
        _build_forward_start_dates(
            reference_date=(
                base_curve.reference_date
            ),
            last_supported_date=(
                base_curve.last_node_date
            ),
            forward_period_days=(
                forward_period_days
            ),
            grid_step_days=(
                grid_step_days
            ),
        )
    )

    perturbation_results: list[
        CentralQuotePerturbationResult
    ] = []

    for shock_index, quote in enumerate(
        quotes
    ):
        plus_quotes = (
            _build_perturbed_quotes(
                quotes=quotes,
                shock_index=shock_index,
                bump_bp=bump_bp,
            )
        )

        minus_quotes = (
            _build_perturbed_quotes(
                quotes=quotes,
                shock_index=shock_index,
                bump_bp=-bump_bp,
            )
        )

        plus_result = (
            bootstrap_ftiie_ois_curve(
                quotes=plus_quotes,
                calendar=calendar,
            )
        )

        minus_result = (
            bootstrap_ftiie_ois_curve(
                quotes=minus_quotes,
                calendar=calendar,
            )
        )

        node_sensitivities = (
            _calculate_central_node_sensitivities(
                quotes=quotes,
                base_result=base_result,
                plus_result=plus_result,
                minus_result=minus_result,
                shock_index=shock_index,
                bump_bp=bump_bp,
            )
        )

        upstream = [
            item
            for item in node_sensitivities
            if item.is_upstream
        ]

        if upstream:
            maximum_upstream_sensitivity = max(
                abs(
                    item.central_sensitivity_bp_per_bp
                )
                for item in upstream
            )

            maximum_upstream_curvature = max(
                abs(
                    item.curvature_bp_per_bp2
                )
                for item in upstream
            )

        else:
            maximum_upstream_sensitivity = 0.0
            maximum_upstream_curvature = 0.0

        own_node = (
            node_sensitivities[
                shock_index
            ]
        )

        forward_summary = (
            _summarize_central_forward_sensitivity(
                base_curve=base_curve,
                plus_curve=plus_result.curve,
                minus_curve=minus_result.curve,
                forward_start_dates=(
                    forward_start_dates
                ),
                forward_period_days=(
                    forward_period_days
                ),
                bump_bp=bump_bp,
            )
        )

        perturbation_results.append(
            CentralQuotePerturbationResult(
                shock_index=shock_index,
                shock_tenor=quote.tenor,
                bump_bp=bump_bp,
                node_sensitivities=(
                    node_sensitivities
                ),
                forward_summary=(
                    forward_summary
                ),
                maximum_upstream_abs_sensitivity=(
                    maximum_upstream_sensitivity
                ),
                maximum_upstream_abs_curvature=(
                    maximum_upstream_curvature
                ),
                own_node_sensitivity=(
                    own_node
                    .central_sensitivity_bp_per_bp
                ),
                own_node_curvature=(
                    own_node
                    .curvature_bp_per_bp2
                ),
            )
        )

    return CentralQuotePerturbationReport(
        reference_date=(
            base_curve.reference_date
        ),
        bump_bp=bump_bp,
        forward_period_days=(
            forward_period_days
        ),
        grid_step_days=(
            grid_step_days
        ),
        base_result=base_result,
        perturbations=tuple(
            perturbation_results
        ),
    )