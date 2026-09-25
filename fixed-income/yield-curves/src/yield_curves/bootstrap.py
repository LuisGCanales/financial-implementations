"""Sequential bootstrap for F-TIIE OIS curves.

The bootstrap solves one discount-factor node at a time.

For calibration instrument i:

    P_1, ..., P_{i-1}

have already been solved and are kept fixed.

The solver varies only the new terminal discount factor P_i until the
i-th OIS reprices to zero.

The interpolation methodology used between calibrated nodes is
configurable, while the sequential calibration algorithm itself is
shared across methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Protocol, Sequence

from scipy.optimize import brentq

from .calendars import BusinessCalendar
from .curves import (
    CurveInterpolationMethod,
    NodalCurve,
    build_nodal_curve,
)
from .instruments import (
    build_ftiie_ois,
)
from .pricing import (
    calculate_par_rate,
    value_ftiie_ois,
)


class OISCalibrationQuote(Protocol):
    """Minimal interface required by the bootstrap."""

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float


@dataclass(frozen=True, slots=True)
class CalibrationStep:
    """Diagnostics for one sequential bootstrap step."""

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
    """Result of one complete sequential OIS bootstrap."""

    curve: NodalCurve

    steps: tuple[
        CalibrationStep,
        ...
    ]

    interpolation_method: CurveInterpolationMethod


def _build_candidate_curve(
    *,
    reference_date: date,
    calibrated_dates: Sequence[date],
    calibrated_dfs: Sequence[float],
    candidate_date: date,
    candidate_df: float,
    interpolation_method: CurveInterpolationMethod,
) -> NodalCurve:
    """Build temporary curve used by one root-solver evaluation.

    Previously solved nodes are preserved exactly.

    The only new state variable is `candidate_df`, corresponding to
    the current calibration instrument.
    """

    return build_nodal_curve(
        method=interpolation_method,
        reference_date=reference_date,
        node_dates=(
            tuple(calibrated_dates)
            + (
                candidate_date,
            )
        ),
        discount_factors=(
            tuple(calibrated_dfs)
            + (
                candidate_df,
            )
        ),
    )


def bootstrap_ftiie_ois_curve_with_method(
    *,
    quotes: Sequence[OISCalibrationQuote],
    calendar: BusinessCalendar,
    interpolation_method: CurveInterpolationMethod,
    bracket_lower_df: float = 1e-6,
    bracket_upper_df: float = 2.0,
    xtol: float = 1e-14,
    rtol: float = 1e-12,
    maxiter: int = 200,
) -> BootstrapResult:
    """Bootstrap an F-TIIE OIS curve with a selected interpolation method.

    Parameters
    ----------
    quotes
        Calibration OIS par quotes, ordered by increasing maturity.

    calendar
        Business-day calendar used to reconstruct each OIS.

    interpolation_method
        Rule used to reconstruct discount factors between calibrated
        nodes.

        Current supported methods:

            LOG_LINEAR_DF
            LINEAR_CONTINUOUS_ZERO

    bracket_lower_df
        Lower discount-factor bound supplied to Brent.

    bracket_upper_df
        Upper discount-factor bound supplied to Brent.

        Values above 1 are deliberately permitted so the framework
        does not rule out negative-rate environments by construction.

    xtol, rtol, maxiter
        Brent root-solver configuration.

    Returns
    -------
    BootstrapResult
        Final calibrated nodal curve plus one diagnostic record per
        calibration instrument.

    Notes
    -----
    Core-v1 uses the same curve for F-TIIE projection and discounting.

    The curve reference date is the effective date of the first OIS.

    The calibration pillar is the final payment date rather than the
    adjusted maturity date. This is an explicit project decision that
    ensures every cash flow required to value the instrument remains
    inside the supported curve domain, avoiding extrapolation caused
    by the payment lag.
    """

    if interpolation_method in {
        CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
        CurveInterpolationMethod.PCHIP_CONTINUOUS_ZERO,
    }:
        raise ValueError(
            f"{interpolation_method.value} may alter "
            "previously represented intervals when new "
            "nodes are introduced and is not supported "
            "by the sequential bootstrap. Use simultaneous "
            "nodal calibration."
        )
        
    if not quotes:
        raise ValueError(
            "At least one calibration quote is required."
        )

    if not (
        isfinite(bracket_lower_df)
        and isfinite(bracket_upper_df)
    ):
        raise ValueError(
            "Bootstrap DF bracket must be finite."
        )

    if bracket_lower_df <= 0.0:
        raise ValueError(
            "Bootstrap lower DF bound must be positive."
        )

    if bracket_upper_df <= bracket_lower_df:
        raise ValueError(
            "Bootstrap upper DF bound must exceed lower bound."
        )

    calibrated_dates: list[date] = []
    calibrated_dfs: list[float] = []

    calibration_steps: list[
        CalibrationStep
    ] = []

    reference_date: date | None = None
    previous_pillar_date: date | None = None

    for quote in quotes:
        if not isfinite(
            quote.par_rate
        ):
            raise ValueError(
                f"Calibration quote for {quote.tenor} "
                "is not finite."
            )

        # ----------------------------------------------------------
        # Reconstruct calibration instrument from the quote.
        # ----------------------------------------------------------

        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        # ----------------------------------------------------------
        # Establish and enforce one common curve reference date.
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # Project decision:
        #
        # pillar = final payment date
        #
        # rather than adjusted maturity date.
        # ----------------------------------------------------------

        pillar_date = (
            ois.final_payment_date
        )

        if (
            previous_pillar_date is not None
            and pillar_date
            <= previous_pillar_date
        ):
            raise ValueError(
                "Calibration pillar dates must be "
                "strictly increasing."
            )

        previous_pillar_date = (
            pillar_date
        )

        # ----------------------------------------------------------
        # Scalar root objective.
        #
        # At instrument i:
        #
        # calibrated_dfs
        # =
        # [P1, ..., P(i-1)]
        #
        # candidate_df
        # =
        # Pi
        #
        # Only Pi changes inside Brent.
        # ----------------------------------------------------------

        def objective(
            candidate_df: float,
        ) -> float:
            candidate_curve = (
                _build_candidate_curve(
                    reference_date=(
                        reference_date
                    ),
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
                    interpolation_method=(
                        interpolation_method
                    ),
                )
            )

            valuation = (
                value_ftiie_ois(
                    ois=ois,
                    projection_curve=(
                        candidate_curve
                    ),
                    discount_curve=(
                        candidate_curve
                    ),
                )
            )

            return (
                valuation
                .npv_receive_float_pay_fixed
            )

        # ----------------------------------------------------------
        # Check that the user-specified DF bracket actually brackets
        # the NPV root.
        # ----------------------------------------------------------

        lower_npv = objective(
            bracket_lower_df
        )

        upper_npv = objective(
            bracket_upper_df
        )

        if not (
            isfinite(lower_npv)
            and isfinite(upper_npv)
        ):
            raise RuntimeError(
                f"Non-finite bootstrap objective for "
                f"{quote.tenor}."
            )

        if lower_npv == 0.0:
            solved_df = (
                bracket_lower_df
            )

            iterations = 0
            function_calls = 1
            converged = True

        elif upper_npv == 0.0:
            solved_df = (
                bracket_upper_df
            )

            iterations = 0
            function_calls = 1
            converged = True

        else:
            if (
                lower_npv
                * upper_npv
                > 0.0
            ):
                raise RuntimeError(
                    f"Bootstrap root is not bracketed "
                    f"for {quote.tenor}: "
                    f"NPV({bracket_lower_df})="
                    f"{lower_npv:.12g}, "
                    f"NPV({bracket_upper_df})="
                    f"{upper_npv:.12g}."
                )

            (
                solved_df,
                root_result,
            ) = brentq(
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

            # +2 accounts for the explicit bracket evaluations above.
            function_calls = (
                root_result.function_calls
                + 2
            )

            converged = (
                root_result.converged
            )

        if (
            not isfinite(solved_df)
            or solved_df <= 0.0
        ):
            raise RuntimeError(
                f"Bootstrap produced invalid discount "
                f"factor for {quote.tenor}: "
                f"{solved_df}."
            )

        if not converged:
            raise RuntimeError(
                f"Bootstrap solver did not converge "
                f"for {quote.tenor}."
            )

        # ----------------------------------------------------------
        # Freeze newly solved node.
        #
        # This is the exact point where:
        #
        # [P1, ..., P(i-1)]
        #
        # becomes:
        #
        # [P1, ..., P(i-1), Pi]
        #
        # The next calibration instrument therefore sees every
        # previously calibrated node as fixed.
        # ----------------------------------------------------------

        calibrated_dates.append(
            pillar_date
        )

        calibrated_dfs.append(
            solved_df
        )

        # ----------------------------------------------------------
        # Rebuild curve including the newly solved node and calculate
        # diagnostics for this calibration step.
        # ----------------------------------------------------------

        solved_curve = (
            build_nodal_curve(
                method=(
                    interpolation_method
                ),
                reference_date=(
                    reference_date
                ),
                node_dates=tuple(
                    calibrated_dates
                ),
                discount_factors=tuple(
                    calibrated_dfs
                ),
            )
        )

        model_quote = (
            calculate_par_rate(
                ois=ois,
                projection_curve=(
                    solved_curve
                ),
                discount_curve=(
                    solved_curve
                ),
            )
        )

        quote_error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000.0

        solved_valuation = (
            value_ftiie_ois(
                ois=ois,
                projection_curve=(
                    solved_curve
                ),
                discount_curve=(
                    solved_curve
                ),
            )
        )

        calibration_steps.append(
            CalibrationStep(
                tenor=quote.tenor,
                market_quote=(
                    quote.par_rate
                ),
                model_quote=model_quote,
                quote_error_bp=(
                    quote_error_bp
                ),
                pillar_date=(
                    pillar_date
                ),
                solved_discount_factor=(
                    solved_df
                ),
                npv_at_solution=(
                    solved_valuation
                    .npv_receive_float_pay_fixed
                ),
                bracket_lower_df=(
                    bracket_lower_df
                ),
                bracket_upper_df=(
                    bracket_upper_df
                ),
                iterations=iterations,
                function_calls=(
                    function_calls
                ),
                converged=converged,
            )
        )

    # We know reference_date cannot remain None because quotes is
    # non-empty and the loop completed.
    assert (
        reference_date
        is not None
    )

    # --------------------------------------------------------------
    # Final curve includes every solved calibration node.
    # --------------------------------------------------------------

    final_curve = (
        build_nodal_curve(
            method=(
                interpolation_method
            ),
            reference_date=(
                reference_date
            ),
            node_dates=tuple(
                calibrated_dates
            ),
            discount_factors=tuple(
                calibrated_dfs
            ),
        )
    )

    return BootstrapResult(
        curve=final_curve,
        steps=tuple(
            calibration_steps
        ),
        interpolation_method=(
            interpolation_method
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
    """Bootstrap the canonical F-TIIE curve.

    Canonical interpolation methodology:

        LOG_LINEAR_DF

    This wrapper preserves the original public API while delegating
    the actual calibration algorithm to
    `bootstrap_ftiie_ois_curve_with_method`.
    """

    return (
        bootstrap_ftiie_ois_curve_with_method(
            quotes=quotes,
            calendar=calendar,
            interpolation_method=(
                CurveInterpolationMethod
                .LOG_LINEAR_DF
            ),
            bracket_lower_df=(
                bracket_lower_df
            ),
            bracket_upper_df=(
                bracket_upper_df
            ),
            xtol=xtol,
            rtol=rtol,
            maxiter=maxiter,
        )
    )