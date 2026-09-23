"""Simultaneous nodal calibration for F-TIIE OIS curves.

Unlike the canonical sequential bootstrap, this calibration engine
solves all nodal discount factors simultaneously.

It is required for interpolation methods whose value on earlier
segments can change when later nodes are introduced, such as a global
cubic spline.

Optimization variables are log discount factors:

    x_i = ln(P_i)

so positive discount factors are guaranteed by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import exp, log
from typing import Sequence

import numpy as np
from scipy.optimize import least_squares

from .bootstrap import (
    OISCalibrationQuote,
    bootstrap_ftiie_ois_curve,
)
from .calendars import BusinessCalendar
from .curves import (
    CurveInterpolationMethod,
    NodalCurve,
    build_nodal_curve,
)
from .instruments import (
    FTiieOIS,
    build_ftiie_ois,
)
from .pricing import (
    calculate_par_rate,
)


@dataclass(frozen=True, slots=True)
class GlobalCalibrationInstrument:
    """Prepared calibration instrument and its market quote."""

    tenor: str
    market_quote: float
    ois: FTiieOIS
    pillar_date: date


@dataclass(frozen=True, slots=True)
class GlobalCalibrationCheck:
    """Final repricing result for one calibration instrument."""

    tenor: str

    market_quote: float
    model_quote: float

    error_bp: float


@dataclass(frozen=True, slots=True)
class GlobalCalibrationResult:
    """Result of simultaneous nodal calibration."""

    curve: NodalCurve

    interpolation_method: CurveInterpolationMethod

    checks: tuple[
        GlobalCalibrationCheck,
        ...
    ]

    success: bool
    message: str

    function_evaluations: int
    jacobian_evaluations: int | None

    cost: float
    optimality: float

    max_abs_repricing_error_bp: float
    rmse_repricing_error_bp: float


def _prepare_global_calibration_instruments(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
) -> tuple[
    date,
    tuple[
        GlobalCalibrationInstrument,
        ...
    ],
]:
    """Reconstruct all calibration OIS instruments."""

    if not quotes:
        raise ValueError(
            "At least one calibration quote is required."
        )

    instruments: list[
        GlobalCalibrationInstrument
    ] = []

    reference_date: date | None = None
    previous_pillar: date | None = None

    for quote in quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        if reference_date is None:
            reference_date = (
                ois.effective_date
            )

        elif (
            ois.effective_date
            != reference_date
        ):
            raise ValueError(
                "All calibration instruments must share "
                "the same effective/reference date."
            )

        pillar_date = (
            ois.final_payment_date
        )

        if (
            previous_pillar is not None
            and pillar_date <= previous_pillar
        ):
            raise ValueError(
                "Calibration pillar dates must be "
                "strictly increasing."
            )

        previous_pillar = pillar_date

        instruments.append(
            GlobalCalibrationInstrument(
                tenor=quote.tenor,
                market_quote=quote.par_rate,
                ois=ois,
                pillar_date=pillar_date,
            )
        )

    assert reference_date is not None

    return (
        reference_date,
        tuple(
            instruments
        ),
    )


def calibrate_ftiie_ois_curve_simultaneously(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    interpolation_method: CurveInterpolationMethod,
    lower_df_bound: float = 1e-6,
    upper_df_bound: float = 2.0,
    repricing_scale_bp: float = 10_000.0,
    ftol: float = 1e-13,
    xtol: float = 1e-13,
    gtol: float = 1e-13,
    max_nfev: int = 5_000,
) -> GlobalCalibrationResult:
    """Calibrate all nodal discount factors simultaneously.

    A canonical log-linear sequential bootstrap is used only to
    provide a robust initial guess.

    The final solution is determined by the requested interpolation
    method and the simultaneous calibration objective.
    """

    if lower_df_bound <= 0:
        raise ValueError(
            "Lower DF bound must be positive."
        )

    if upper_df_bound <= lower_df_bound:
        raise ValueError(
            "Upper DF bound must exceed lower DF bound."
        )

    (
        reference_date,
        instruments,
    ) = _prepare_global_calibration_instruments(
        quotes=quotes,
        calendar=calendar,
    )

    pillar_dates = tuple(
        instrument.pillar_date
        for instrument in instruments
    )

    # --------------------------------------------------------------
    # Initial guess only.
    #
    # This does NOT constrain the global solution to the canonical
    # curve. It simply provides a financially sensible starting point.
    # --------------------------------------------------------------

    initial_bootstrap = (
        bootstrap_ftiie_ois_curve(
            quotes=quotes,
            calendar=calendar,
        )
    )

    initial_log_dfs = np.array(
        [
            log(discount_factor)
            for discount_factor
            in initial_bootstrap
            .curve
            .discount_factors
        ],
        dtype=float,
    )

    lower_log_df = log(
        lower_df_bound
    )

    upper_log_df = log(
        upper_df_bound
    )

    def residuals(
        log_dfs: np.ndarray,
    ) -> np.ndarray:
        discount_factors = tuple(
            exp(float(value))
            for value in log_dfs
        )

        curve = build_nodal_curve(
            method=interpolation_method,
            reference_date=reference_date,
            node_dates=pillar_dates,
            discount_factors=(
                discount_factors
            ),
        )

        errors = []

        for instrument in instruments:
            model_quote = (
                calculate_par_rate(
                    ois=instrument.ois,
                    projection_curve=curve,
                    discount_curve=curve,
                )
            )

            errors.append(
                (
                    model_quote
                    - instrument.market_quote
                )
                * repricing_scale_bp
            )

        return np.asarray(
            errors,
            dtype=float,
        )

    optimization = least_squares(
        residuals,
        initial_log_dfs,
        bounds=(
            lower_log_df,
            upper_log_df,
        ),
        ftol=ftol,
        xtol=xtol,
        gtol=gtol,
        max_nfev=max_nfev,
    )

    solved_dfs = tuple(
        exp(float(value))
        for value in optimization.x
    )

    final_curve = build_nodal_curve(
        method=interpolation_method,
        reference_date=reference_date,
        node_dates=pillar_dates,
        discount_factors=solved_dfs,
    )

    checks: list[
        GlobalCalibrationCheck
    ] = []

    errors_bp: list[float] = []

    for instrument in instruments:
        model_quote = (
            calculate_par_rate(
                ois=instrument.ois,
                projection_curve=final_curve,
                discount_curve=final_curve,
            )
        )

        error_bp = (
            model_quote
            - instrument.market_quote
        ) * 10_000.0

        errors_bp.append(
            error_bp
        )

        checks.append(
            GlobalCalibrationCheck(
                tenor=instrument.tenor,
                market_quote=(
                    instrument.market_quote
                ),
                model_quote=model_quote,
                error_bp=error_bp,
            )
        )

    max_abs_error = max(
        abs(error)
        for error in errors_bp
    )

    rmse = (
        sum(
            error * error
            for error in errors_bp
        )
        / len(errors_bp)
    ) ** 0.5

    return GlobalCalibrationResult(
        curve=final_curve,
        interpolation_method=(
            interpolation_method
        ),
        checks=tuple(
            checks
        ),
        success=bool(
            optimization.success
        ),
        message=str(
            optimization.message
        ),
        function_evaluations=int(
            optimization.nfev
        ),
        jacobian_evaluations=(
            None
            if optimization.njev is None
            else int(
                optimization.njev
            )
        ),
        cost=float(
            optimization.cost
        ),
        optimality=float(
            optimization.optimality
        ),
        max_abs_repricing_error_bp=(
            max_abs_error
        ),
        rmse_repricing_error_bp=(
            rmse
        ),
    )