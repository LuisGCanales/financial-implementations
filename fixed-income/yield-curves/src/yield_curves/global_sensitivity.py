"""Sensitivity diagnostics for simultaneous F-TIIE curve calibration.

This module studies how globally calibrated nodal curves respond to
symmetric one-factor-at-a-time market-quote perturbations.

Financial/calibration logic remains side-effect free by default.  An optional
``progress_callback`` can be supplied by scripts or tests when operational
progress logging is useful during expensive experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum, isfinite, sqrt
from time import perf_counter
from typing import Callable, Sequence

from .bootstrap import OISCalibrationQuote
from .calendars import BusinessCalendar
from .calibration import (
    GlobalCalibrationResult,
    calibrate_ftiie_ois_curve_simultaneously,
)
from .curves import CurveInterpolationMethod


ProgressCallback = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class PerturbedGlobalQuote:
    """Minimal calibration quote used by quote-shock experiments."""

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float


@dataclass(frozen=True, slots=True)
class GlobalNodeSensitivity:
    """Central node-zero response to one symmetric market-quote shock."""

    shock_tenor: str
    node_tenor: str

    shock_index: int
    node_index: int

    node_date: date

    central_sensitivity_bp_per_bp: float
    curvature_bp_per_bp2: float

    maturity_distance: int


@dataclass(frozen=True, slots=True)
class GlobalForwardSensitivityObservation:
    """One dense-grid forward observation under a symmetric quote shock."""

    start_date: date
    end_date: date

    base_forward_rate: float
    plus_forward_rate: float
    minus_forward_rate: float

    central_sensitivity_bp_per_bp: float
    curvature_bp_per_bp2: float


@dataclass(frozen=True, slots=True)
class GlobalForwardSensitivity:
    """Dense forward response to one symmetric market-quote shock."""

    observation_count: int

    sensitivity_bias: float
    sensitivity_mae: float
    sensitivity_rmse: float

    maximum_abs_sensitivity: float
    maximum_abs_sensitivity_date: date

    curvature_rmse: float
    maximum_abs_curvature: float
    maximum_abs_curvature_date: date

    observations: tuple[
        GlobalForwardSensitivityObservation,
        ...,
    ]


@dataclass(frozen=True, slots=True)
class GlobalQuoteShockResult:
    """Response of one globally calibrated curve to one quote shock."""

    shock_index: int
    shock_tenor: str
    bump_bp: float

    node_sensitivities: tuple[
        GlobalNodeSensitivity,
        ...,
    ]

    forward_sensitivity: GlobalForwardSensitivity

    own_node_sensitivity: float
    own_node_curvature: float

    maximum_abs_node_sensitivity: float
    maximum_abs_node_sensitivity_tenor: str

    total_abs_node_sensitivity: float
    off_diagonal_abs_sensitivity: float
    off_diagonal_share: float

    plus_calibration_success: bool
    minus_calibration_success: bool

    plus_max_abs_repricing_error_bp: float
    minus_max_abs_repricing_error_bp: float
    
    forward_locality: ForwardSensitivityLocality


@dataclass(frozen=True, slots=True)
class ForwardSensitivityLocality:
    """Locality diagnostics for a dense forward-sensitivity response.

    The absolute central forward sensitivities are interpreted as a
    discrete sensitivity-mass distribution across forward-start
    maturities:

        w_j = |dF_j / dK_i| / sum_k |dF_k / dK_i|

    where K_i is the shocked market quote.

    The primary locality metric is the RMS distance from the shocked
    quote's calibrated pillar:

        L_i = sqrt(
            sum_j w_j * (t_j - T_i)^2
        )

    Smaller values indicate a response concentrated closer to the
    shocked maturity.

    The weighted spread around the sensitivity center and the center
    offset from the shocked maturity are also retained because:

        L_i^2
        =
        weighted_spread^2
        +
        center_offset^2

    All maturity distances are expressed in ACT/360 years.
    """

    observation_count: int

    shock_pillar_years: float

    weighted_center_years: float

    center_offset_from_shock_years: float

    weighted_spread_years: float

    rms_distance_from_shock_years: float

    sensitivity_mass_within_1y: float

    sensitivity_mass_within_2y: float
    

@dataclass(frozen=True, slots=True)
class GlobalSensitivityReport:
    """Complete simultaneous-calibration quote-sensitivity experiment."""

    interpolation_method: CurveInterpolationMethod
    reference_date: date

    bump_bp: float
    forward_period_days: int
    grid_step_days: int

    base_calibration: GlobalCalibrationResult

    shocks: tuple[
        GlobalQuoteShockResult,
        ...,
    ]


def _emit_progress(
    progress_callback: ProgressCallback | None,
    message: str,
) -> None:
    """Emit an operational progress message only when requested."""

    if progress_callback is not None:
        progress_callback(
            message
        )


def _perturb_quotes(
    *,
    quotes: Sequence[OISCalibrationQuote],
    shock_index: int,
    bump_bp: float,
) -> tuple[PerturbedGlobalQuote, ...]:
    """Return a quote set with exactly one selected quote perturbed."""

    if shock_index < 0 or shock_index >= len(quotes):
        raise IndexError(
            "Shock index is outside the calibration quote set."
        )

    bump_rate = (
        bump_bp
        / 10_000.0
    )

    result: list[
        PerturbedGlobalQuote
    ] = []

    for index, quote in enumerate(
        quotes
    ):
        par_rate = (
            quote.par_rate
            + (
                bump_rate
                if index == shock_index
                else 0.0
            )
        )

        result.append(
            PerturbedGlobalQuote(
                tenor=quote.tenor,
                trade_date=quote.trade_date,
                contractual_maturity_date=(
                    quote.contractual_maturity_date
                ),
                par_rate=par_rate,
            )
        )

    return tuple(
        result
    )


def _forward_start_dates(
    *,
    reference_date: date,
    last_date: date,
    forward_period_days: int,
    grid_step_days: int,
) -> tuple[date, ...]:
    """Build a deterministic dense grid of forward start dates."""

    if forward_period_days <= 0:
        raise ValueError(
            "Forward period must be positive."
        )

    if grid_step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    if last_date <= reference_date:
        raise ValueError(
            "Last supported date must follow the reference date."
        )

    last_start = (
        last_date
        - timedelta(
            days=forward_period_days
        )
    )

    if last_start < reference_date:
        raise ValueError(
            "Curve horizon is shorter than the forward period."
        )

    dates: list[date] = []

    current = (
        reference_date
    )

    while current <= last_start:
        dates.append(
            current
        )

        current += timedelta(
            days=grid_step_days
        )

    return tuple(
        dates
    )


def _calculate_forward_sensitivity(
    *,
    base_curve,
    plus_curve,
    minus_curve,
    dates: Sequence[date],
    bump_bp: float,
    forward_period_days: int,
) -> GlobalForwardSensitivity:
    """Calculate dense central forward sensitivity and curvature."""

    if not dates:
        raise ValueError(
            "Forward sensitivity requires at least one observation date."
        )

    if bump_bp <= 0.0:
        raise ValueError(
            "Sensitivity bump must be positive."
        )

    if forward_period_days <= 0:
        raise ValueError(
            "Forward period must be positive."
        )

    observations: list[
        GlobalForwardSensitivityObservation
    ] = []

    sensitivities: list[float] = []
    curvatures: list[float] = []

    for start_date in dates:
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

        sensitivity = (
            (
                plus_forward
                - minus_forward
            )
            * 10_000.0
            / (
                2.0
                * bump_bp
            )
        )

        curvature = (
            (
                plus_forward
                - 2.0 * base_forward
                + minus_forward
            )
            * 10_000.0
            / (
                bump_bp ** 2
            )
        )

        if not (
            isfinite(base_forward)
            and isfinite(plus_forward)
            and isfinite(minus_forward)
            and isfinite(sensitivity)
            and isfinite(curvature)
        ):
            raise RuntimeError(
                "Forward sensitivity calculation produced a non-finite value."
            )

        sensitivities.append(
            sensitivity
        )

        curvatures.append(
            curvature
        )

        observations.append(
            GlobalForwardSensitivityObservation(
                start_date=start_date,
                end_date=end_date,
                base_forward_rate=base_forward,
                plus_forward_rate=plus_forward,
                minus_forward_rate=minus_forward,
                central_sensitivity_bp_per_bp=(
                    sensitivity
                ),
                curvature_bp_per_bp2=(
                    curvature
                ),
            )
        )

    count = len(
        sensitivities
    )

    bias = (
        fsum(
            sensitivities
        )
        / count
    )

    mae = (
        fsum(
            abs(value)
            for value in sensitivities
        )
        / count
    )

    rmse = sqrt(
        fsum(
            value * value
            for value in sensitivities
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

    sensitivity_max_index = max(
        range(count),
        key=lambda index: abs(
            sensitivities[index]
        ),
    )

    curvature_max_index = max(
        range(count),
        key=lambda index: abs(
            curvatures[index]
        ),
    )

    return GlobalForwardSensitivity(
        observation_count=count,
        sensitivity_bias=bias,
        sensitivity_mae=mae,
        sensitivity_rmse=rmse,
        maximum_abs_sensitivity=abs(
            sensitivities[
                sensitivity_max_index
            ]
        ),
        maximum_abs_sensitivity_date=(
            observations[
                sensitivity_max_index
            ].start_date
        ),
        curvature_rmse=curvature_rmse,
        maximum_abs_curvature=abs(
            curvatures[
                curvature_max_index
            ]
        ),
        maximum_abs_curvature_date=(
            observations[
                curvature_max_index
            ].start_date
        ),
        observations=tuple(
            observations
        ),
    )


def calculate_forward_sensitivity_locality(
    *,
    reference_date: date,
    shock_pillar_date: date,
    forward_start_dates: Sequence[date],
    sensitivities_bp_per_bp: Sequence[float],
) -> ForwardSensitivityLocality:
    """Calculate locality diagnostics for one quote-to-forward shock.

    Parameters
    ----------
    reference_date
        Curve reference date.

    shock_pillar_date
        Calibrated pillar date associated with the shocked market quote.

    forward_start_dates
        Dense forward-start dates.

    sensitivities_bp_per_bp
        Central forward sensitivities corresponding one-for-one with
        ``forward_start_dates``.

    Returns
    -------
    ForwardSensitivityLocality
        Absolute-sensitivity-weighted locality diagnostics.

    Notes
    -----
    Absolute sensitivities are used as weights because positive and
    negative compensating responses should not cancel when measuring
    how broadly a shock propagates through the forward curve.

    This metric measures propagation geometry, not total sensitivity
    magnitude. Magnitude remains captured separately by metrics such
    as forward sensitivity RMSE and maximum absolute sensitivity.
    """

    if not forward_start_dates:
        raise ValueError(
            "At least one forward sensitivity observation is required."
        )

    if (
        len(forward_start_dates)
        != len(sensitivities_bp_per_bp)
    ):
        raise ValueError(
            "Forward-start dates and sensitivities "
            "must have equal length."
        )

    if shock_pillar_date < reference_date:
        raise ValueError(
            "Shock pillar date cannot precede "
            "the curve reference date."
        )

    times_years: list[float] = []

    absolute_sensitivities: list[float] = []

    for (
        start_date,
        sensitivity,
    ) in zip(
        forward_start_dates,
        sensitivities_bp_per_bp,
    ):
        if start_date < reference_date:
            raise ValueError(
                "Forward-start dates cannot precede "
                "the curve reference date."
            )

        sensitivity = float(
            sensitivity
        )

        if not isfinite(
            sensitivity
        ):
            raise ValueError(
                "Forward sensitivities must be finite."
            )

        time_years = (
            start_date
            - reference_date
        ).days / 360.0

        times_years.append(
            time_years
        )

        absolute_sensitivities.append(
            abs(
                sensitivity
            )
        )

    total_absolute_sensitivity = (
        fsum(
            absolute_sensitivities
        )
    )

    if total_absolute_sensitivity <= 0.0:
        raise ValueError(
            "Forward-sensitivity locality is undefined "
            "when all sensitivities are zero."
        )

    weights = [
        value
        / total_absolute_sensitivity
        for value
        in absolute_sensitivities
    ]

    shock_pillar_years = (
        shock_pillar_date
        - reference_date
    ).days / 360.0

    weighted_center_years = (
        fsum(
            weight
            * time_years
            for (
                weight,
                time_years,
            ) in zip(
                weights,
                times_years,
            )
        )
    )

    center_offset = (
        weighted_center_years
        - shock_pillar_years
    )

    weighted_variance = (
        fsum(
            weight
            * (
                time_years
                - weighted_center_years
            ) ** 2
            for (
                weight,
                time_years,
            ) in zip(
                weights,
                times_years,
            )
        )
    )

    weighted_spread = sqrt(
        max(
            weighted_variance,
            0.0,
        )
    )

    rms_distance = sqrt(
        fsum(
            weight
            * (
                time_years
                - shock_pillar_years
            ) ** 2
            for (
                weight,
                time_years,
            ) in zip(
                weights,
                times_years,
            )
        )
    )

    sensitivity_mass_within_1y = (
        fsum(
            weight
            for (
                weight,
                time_years,
            ) in zip(
                weights,
                times_years,
            )
            if (
                abs(
                    time_years
                    - shock_pillar_years
                )
                <= 1.0
            )
        )
    )

    sensitivity_mass_within_2y = (
        fsum(
            weight
            for (
                weight,
                time_years,
            ) in zip(
                weights,
                times_years,
            )
            if (
                abs(
                    time_years
                    - shock_pillar_years
                )
                <= 2.0
            )
        )
    )

    return ForwardSensitivityLocality(
        observation_count=(
            len(
                forward_start_dates
            )
        ),
        shock_pillar_years=(
            shock_pillar_years
        ),
        weighted_center_years=(
            weighted_center_years
        ),
        center_offset_from_shock_years=(
            center_offset
        ),
        weighted_spread_years=(
            weighted_spread
        ),
        rms_distance_from_shock_years=(
            rms_distance
        ),
        sensitivity_mass_within_1y=(
            sensitivity_mass_within_1y
        ),
        sensitivity_mass_within_2y=(
            sensitivity_mass_within_2y
        ),
    )
    
    
def analyze_global_quote_sensitivity(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    interpolation_method: CurveInterpolationMethod,
    bump_bp: float = 1.0,
    forward_period_days: int = 28,
    grid_step_days: int = 7,
    progress_callback: ProgressCallback | None = None,
) -> GlobalSensitivityReport:
    """Run symmetric OFAT quote shocks under simultaneous calibration.

    Important performance decisions
    -------------------------------
    * Cheap argument validation happens before any calibration.
    * The base curve is calibrated once.
    * Every +/- quote shock uses the base nodal discount factors as the
      optimizer warm start.
    * Dense forward diagnostics are calculated once and retained in the
      returned structured result.
    * Progress logging is opt-in through ``progress_callback``.
    """

    # ------------------------------------------------------------------
    # Cheap validation first.  Invalid-input tests should never trigger
    # an expensive calibration.
    # ------------------------------------------------------------------

    if not quotes:
        raise ValueError(
            "At least one calibration quote is required."
        )

    if bump_bp <= 0.0:
        raise ValueError(
            "Sensitivity bump must be positive."
        )

    if forward_period_days <= 0:
        raise ValueError(
            "Forward period must be positive."
        )

    if grid_step_days <= 0:
        raise ValueError(
            "Grid step must be positive."
        )

    experiment_started = perf_counter()

    _emit_progress(
        progress_callback,
        (
            "base calibration starting | "
            f"method={interpolation_method.value} | "
            f"quotes={len(quotes)}"
        ),
    )

    base_started = perf_counter()

    base = (
        calibrate_ftiie_ois_curve_simultaneously(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                interpolation_method
            ),
        )
    )

    base_elapsed = (
        perf_counter()
        - base_started
    )

    _emit_progress(
        progress_callback,
        (
            "base calibration finished | "
            f"elapsed={base_elapsed:.2f}s | "
            f"success={base.success} | "
            f"nfev={base.function_evaluations} | "
            "max_repricing_error_bp="
            f"{base.max_abs_repricing_error_bp:.8f}"
        ),
    )

    if not base.success:
        raise RuntimeError(
            "Base simultaneous calibration failed: "
            f"{base.message}"
        )

    base_curve = (
        base.curve
    )

    base_discount_factors = tuple(
        base_curve.discount_factors
    )

    forward_dates = (
        _forward_start_dates(
            reference_date=(
                base_curve.reference_date
            ),
            last_date=(
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

    _emit_progress(
        progress_callback,
        (
            "dense forward grid prepared | "
            f"observations={len(forward_dates)} | "
            f"step_days={grid_step_days} | "
            f"forward_days={forward_period_days}"
        ),
    )

    shocks: list[
        GlobalQuoteShockResult
    ] = []

    shock_count = len(
        quotes
    )

    for shock_index, quote in enumerate(
        quotes
    ):
        shock_number = (
            shock_index
            + 1
        )

        shock_started = perf_counter()

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] starting"
            ),
        )

        plus_quotes = (
            _perturb_quotes(
                quotes=quotes,
                shock_index=shock_index,
                bump_bp=bump_bp,
            )
        )

        minus_quotes = (
            _perturb_quotes(
                quotes=quotes,
                shock_index=shock_index,
                bump_bp=-bump_bp,
            )
        )

        # --------------------------------------------------------------
        # + bump calibration.
        # --------------------------------------------------------------

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] +{bump_bp:g}bp calibration starting"
            ),
        )

        plus_started = perf_counter()

        plus = (
            calibrate_ftiie_ois_curve_simultaneously(
                quotes=plus_quotes,
                calendar=calendar,
                interpolation_method=(
                    interpolation_method
                ),
                initial_discount_factors=(
                    base_discount_factors
                ),
            )
        )

        plus_elapsed = (
            perf_counter()
            - plus_started
        )

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] +{bump_bp:g}bp calibration finished | "
                f"elapsed={plus_elapsed:.2f}s | "
                f"success={plus.success} | "
                f"nfev={plus.function_evaluations} | "
                "max_repricing_error_bp="
                f"{plus.max_abs_repricing_error_bp:.8f}"
            ),
        )

        # --------------------------------------------------------------
        # - bump calibration.
        # --------------------------------------------------------------

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] -{bump_bp:g}bp calibration starting"
            ),
        )

        minus_started = perf_counter()

        minus = (
            calibrate_ftiie_ois_curve_simultaneously(
                quotes=minus_quotes,
                calendar=calendar,
                interpolation_method=(
                    interpolation_method
                ),
                initial_discount_factors=(
                    base_discount_factors
                ),
            )
        )

        minus_elapsed = (
            perf_counter()
            - minus_started
        )

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] -{bump_bp:g}bp calibration finished | "
                f"elapsed={minus_elapsed:.2f}s | "
                f"success={minus.success} | "
                f"nfev={minus.function_evaluations} | "
                "max_repricing_error_bp="
                f"{minus.max_abs_repricing_error_bp:.8f}"
            ),
        )

        if (
            not plus.success
            or not minus.success
        ):
            raise RuntimeError(
                f"Perturbed calibration failed for {quote.tenor}. "
                f"plus_success={plus.success}, "
                f"minus_success={minus.success}"
            )

        if not (
            base.curve.node_dates
            == plus.curve.node_dates
            == minus.curve.node_dates
        ):
            raise RuntimeError(
                "Perturbed calibrations changed node dates."
            )

        # --------------------------------------------------------------
        # Node-zero Jacobian / curvature.
        # --------------------------------------------------------------

        node_results: list[
            GlobalNodeSensitivity
        ] = []

        for node_index, (
            node_quote,
            node_date,
        ) in enumerate(
            zip(
                quotes,
                base.curve.node_dates,
            )
        ):
            base_zero = (
                base.curve.zero_rate(
                    node_date
                )
            )

            plus_zero = (
                plus.curve.zero_rate(
                    node_date
                )
            )

            minus_zero = (
                minus.curve.zero_rate(
                    node_date
                )
            )

            sensitivity = (
                (
                    plus_zero
                    - minus_zero
                )
                * 10_000.0
                / (
                    2.0
                    * bump_bp
                )
            )

            curvature = (
                (
                    plus_zero
                    - 2.0 * base_zero
                    + minus_zero
                )
                * 10_000.0
                / (
                    bump_bp ** 2
                )
            )

            if not (
                isfinite(sensitivity)
                and isfinite(curvature)
            ):
                raise RuntimeError(
                    "Node sensitivity calculation produced "
                    "a non-finite value."
                )

            node_results.append(
                GlobalNodeSensitivity(
                    shock_tenor=quote.tenor,
                    node_tenor=node_quote.tenor,
                    shock_index=shock_index,
                    node_index=node_index,
                    node_date=node_date,
                    central_sensitivity_bp_per_bp=(
                        sensitivity
                    ),
                    curvature_bp_per_bp2=(
                        curvature
                    ),
                    maturity_distance=(
                        node_index
                        - shock_index
                    ),
                )
            )

        absolute_node_sensitivities = [
            abs(
                item.central_sensitivity_bp_per_bp
            )
            for item in node_results
        ]

        total_abs = fsum(
            absolute_node_sensitivities
        )

        own_abs = (
            absolute_node_sensitivities[
                shock_index
            ]
        )

        off_diagonal_abs = (
            total_abs
            - own_abs
        )

        off_diagonal_share = (
            0.0
            if total_abs == 0.0
            else (
                off_diagonal_abs
                / total_abs
            )
        )

        maximum_index = max(
            range(
                len(
                    node_results
                )
            ),
            key=lambda index: (
                absolute_node_sensitivities[
                    index
                ]
            ),
        )

        # --------------------------------------------------------------
        # Dense forward response.
        # --------------------------------------------------------------

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] dense forward diagnostics starting | "
                f"observations={len(forward_dates)}"
            ),
        )

        forward_started = perf_counter()

        forward_sensitivity = (
            _calculate_forward_sensitivity(
                base_curve=(
                    base.curve
                ),
                plus_curve=(
                    plus.curve
                ),
                minus_curve=(
                    minus.curve
                ),
                dates=forward_dates,
                bump_bp=bump_bp,
                forward_period_days=(
                    forward_period_days
                ),
            )
        )

        forward_elapsed = (
            perf_counter()
            - forward_started
        )

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] dense forward diagnostics finished | "
                f"elapsed={forward_elapsed:.2f}s | "
                "rmse_bp_per_bp="
                f"{forward_sensitivity.sensitivity_rmse:.6f} | "
                "max_abs_bp_per_bp="
                f"{forward_sensitivity.maximum_abs_sensitivity:.6f}"
            ),
        )

        forward_locality_started = perf_counter()

        forward_locality = (
            calculate_forward_sensitivity_locality(
                reference_date=(
                    base_curve.reference_date
                ),
                shock_pillar_date=(
                    node_results[
                        shock_index
                    ].node_date
                ),
                forward_start_dates=tuple(
                    observation.start_date
                    for observation
                    in (
                        forward_sensitivity
                        .observations
                    )
                ),
                sensitivities_bp_per_bp=tuple(
                    observation
                    .central_sensitivity_bp_per_bp
                    for observation
                    in (
                        forward_sensitivity
                        .observations
                    )
                ),
            )
        )

        forward_locality_elapsed = (
            perf_counter()
            - forward_locality_started
        )

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] forward locality diagnostics finished | "
                f"elapsed={forward_locality_elapsed:.2f}s | "
                f"rms_distance={forward_locality.rms_distance_from_shock_years:.4f}y | "
                f"spread={forward_locality.weighted_spread_years:.4f}y | "
                f"center_offset="
                f"{forward_locality.center_offset_from_shock_years:+.4f}y | "
                f"mass_within_1y="
                f"{forward_locality.sensitivity_mass_within_1y:.2%} | "
                f"mass_within_2y="
                f"{forward_locality.sensitivity_mass_within_2y:.2%}"
            ),
        )
        
        shocks.append(
            GlobalQuoteShockResult(
                shock_index=shock_index,
                shock_tenor=quote.tenor,
                bump_bp=bump_bp,
                node_sensitivities=tuple(
                    node_results
                ),
                forward_sensitivity=(
                    forward_sensitivity
                ),
                own_node_sensitivity=(
                    node_results[
                        shock_index
                    ].central_sensitivity_bp_per_bp
                ),
                own_node_curvature=(
                    node_results[
                        shock_index
                    ].curvature_bp_per_bp2
                ),
                maximum_abs_node_sensitivity=(
                    absolute_node_sensitivities[
                        maximum_index
                    ]
                ),
                maximum_abs_node_sensitivity_tenor=(
                    node_results[
                        maximum_index
                    ].node_tenor
                ),
                total_abs_node_sensitivity=(
                    total_abs
                ),
                off_diagonal_abs_sensitivity=(
                    off_diagonal_abs
                ),
                off_diagonal_share=(
                    off_diagonal_share
                ),
                plus_calibration_success=(
                    plus.success
                ),
                minus_calibration_success=(
                    minus.success
                ),
                plus_max_abs_repricing_error_bp=(
                    plus.max_abs_repricing_error_bp
                ),
                minus_max_abs_repricing_error_bp=(
                    minus.max_abs_repricing_error_bp
                ),
            )
        )

        shock_elapsed = (
            perf_counter()
            - shock_started
        )

        _emit_progress(
            progress_callback,
            (
                f"shock {shock_number}/{shock_count} "
                f"[{quote.tenor}] complete | "
                f"elapsed={shock_elapsed:.2f}s | "
                "off_diagonal_share="
                f"{off_diagonal_share:.6f}"
            ),
        )

    experiment_elapsed = (
        perf_counter()
        - experiment_started
    )

    _emit_progress(
        progress_callback,
        (
            "global sensitivity experiment complete | "
            f"method={interpolation_method.value} | "
            f"shocks={len(shocks)} | "
            f"elapsed={experiment_elapsed:.2f}s"
        ),
    )

    return GlobalSensitivityReport(
        interpolation_method=(
            interpolation_method
        ),
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
        base_calibration=base,
        shocks=tuple(
            shocks
        ),
    )
