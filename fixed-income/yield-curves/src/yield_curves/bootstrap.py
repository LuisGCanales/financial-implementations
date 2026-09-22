"""Sequential F-TIIE OIS curve calibration.

Core-v1 methodology
-------------------
State variable:
    discount factors

Interpolation:
    log-linear discount factors

Calibration condition:
    quoted OIS NPV = 0

Architecture:
    projection curve = discount curve

Solver:
    bracketed Brent root solver

The bootstrap operates only on quoted instruments.
It has no access to the curve that generated synthetic test data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Protocol, Sequence

from scipy.optimize import brentq

from .calendars import BusinessCalendar
from .curves import (
    LogLinearDiscountCurve,
)
from .instruments import (
    build_ftiie_ois,
)
from .pricing import (
    calculate_par_rate,
    value_ftiie_ois,
)


class OISCalibrationQuote(Protocol):
    """Minimal quote interface required by the bootstrap."""

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float


@dataclass(frozen=True, slots=True)
class CalibrationStep:
    """Diagnostics for one calibrated OIS node."""

    tenor: str

    market_quote: float
    model_quote: float
    quote_error_bp: float

    pillar_date: date
    solved_discount_factor: float

    npv_at_solution: float

    bracket_lower_df: float
    bracket_upper_df: float

    iterations: int
    function_calls: int

    converged: bool


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Final calibrated curve and node-level diagnostics."""

    curve: LogLinearDiscountCurve

    steps: tuple[
        CalibrationStep,
        ...
    ]


def _build_candidate_curve(
    *,
    reference_date: date,
    calibrated_dates: Sequence[date],
    calibrated_dfs: Sequence[float],
    candidate_date: date,
    candidate_df: float,
) -> LogLinearDiscountCurve:
    """Build immutable curve including one candidate terminal node."""

    return LogLinearDiscountCurve(
        reference_date=reference_date,
        node_dates=tuple(
            calibrated_dates
        )
        + (
            candidate_date,
        ),
        discount_factors=tuple(
            calibrated_dfs
        )
        + (
            candidate_df,
        ),
    )


def bootstrap_ftiie_ois_curve(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    bracket_lower_df: float = 1e-6,
    bracket_upper_df: float = 2.0,
    xtol: float = 1e-14,
    rtol: float = 1e-12,
    maxiter: int = 200,
) -> BootstrapResult:
    """Bootstrap Core-v1 F-TIIE OIS curve sequentially.

    Each calibration instrument contributes one new curve node.

    Pillar convention
    -----------------
    The pillar date is the instrument's final payment date.

    This is a PROJECT DECISION.

    It ensures that every cash flow required to value the instrument
    lies inside the candidate curve domain without extrapolation.

    The implementation does not claim this to be CME's production
    pillar convention.
    """

    if not quotes:
        raise ValueError(
            "At least one calibration quote is required."
        )

    if (
        not isfinite(bracket_lower_df)
        or bracket_lower_df <= 0
    ):
        raise ValueError(
            "Lower DF bracket must be finite and positive."
        )

    if (
        not isfinite(bracket_upper_df)
        or bracket_upper_df <= bracket_lower_df
    ):
        raise ValueError(
            "Upper DF bracket must exceed lower bracket."
        )

    reference_date: date | None = None

    calibrated_dates: list[date] = []
    calibrated_dfs: list[float] = []

    steps: list[CalibrationStep] = []

    for quote in quotes:
        if not isfinite(
            quote.par_rate
        ):
            raise ValueError(
                f"Non-finite quote for {quote.tenor}."
            )

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
                "the same effective / curve reference date."
            )

        pillar_date = (
            ois.final_payment_date
        )

        if (
            calibrated_dates
            and pillar_date
            <= calibrated_dates[-1]
        ):
            raise ValueError(
                "Calibration pillar dates must be "
                "strictly increasing."
            )

        def objective(
            candidate_df: float,
        ) -> float:
            candidate_curve = (
                _build_candidate_curve(
                    reference_date=reference_date,
                    calibrated_dates=(
                        calibrated_dates
                    ),
                    calibrated_dfs=(
                        calibrated_dfs
                    ),
                    candidate_date=(
                        pillar_date
                    ),
                    candidate_df=(
                        candidate_df
                    ),
                )
            )

            valuation = value_ftiie_ois(
                ois=ois,
                projection_curve=candidate_curve,
                discount_curve=candidate_curve,
            )

            return (
                valuation
                .npv_receive_float_pay_fixed
            )

        lower_value = objective(
            bracket_lower_df
        )

        upper_value = objective(
            bracket_upper_df
        )

        if lower_value == 0.0:
            solved_df = bracket_lower_df
            iterations = 0
            function_calls = 2
            converged = True

        elif upper_value == 0.0:
            solved_df = bracket_upper_df
            iterations = 0
            function_calls = 2
            converged = True

        else:
            if (
                lower_value
                * upper_value
                > 0
            ):
                raise RuntimeError(
                    "Calibration root is not bracketed for "
                    f"{quote.tenor}. "
                    f"NPV(lower)={lower_value:.12g}, "
                    f"NPV(upper)={upper_value:.12g}."
                )

            solved_df, root_result = brentq(
                objective,
                bracket_lower_df,
                bracket_upper_df,
                xtol=xtol,
                rtol=rtol,
                maxiter=maxiter,
                full_output=True,
                disp=False,
            )

            iterations = (
                root_result.iterations
            )

            function_calls = (
                root_result.function_calls
                + 2
            )

            converged = (
                root_result.converged
            )

        calibrated_dates.append(
            pillar_date
        )

        calibrated_dfs.append(
            solved_df
        )

        calibrated_curve = (
            LogLinearDiscountCurve(
                reference_date=reference_date,
                node_dates=tuple(
                    calibrated_dates
                ),
                discount_factors=tuple(
                    calibrated_dfs
                ),
            )
        )

        model_quote = calculate_par_rate(
            ois=ois,
            projection_curve=calibrated_curve,
            discount_curve=calibrated_curve,
        )

        quote_error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000.0

        valuation = value_ftiie_ois(
            ois=ois,
            projection_curve=calibrated_curve,
            discount_curve=calibrated_curve,
        )

        steps.append(
            CalibrationStep(
                tenor=quote.tenor,
                market_quote=quote.par_rate,
                model_quote=model_quote,
                quote_error_bp=(
                    quote_error_bp
                ),
                pillar_date=pillar_date,
                solved_discount_factor=(
                    solved_df
                ),
                npv_at_solution=(
                    valuation
                    .npv_receive_float_pay_fixed
                ),
                bracket_lower_df=(
                    bracket_lower_df
                ),
                bracket_upper_df=(
                    bracket_upper_df
                ),
                iterations=iterations,
                function_calls=function_calls,
                converged=converged,
            )
        )

    if reference_date is None:
        raise RuntimeError(
            "Bootstrap failed to establish reference date."
        )

    curve = LogLinearDiscountCurve(
        reference_date=reference_date,
        node_dates=tuple(
            calibrated_dates
        ),
        discount_factors=tuple(
            calibrated_dfs
        ),
    )

    return BootstrapResult(
        curve=curve,
        steps=tuple(
            steps
        ),
    )