"""Synthetic known-truth scenarios for curve calibration experiments.

This module generates controlled market-like OIS quotes from a curve
whose underlying discount-factor structure is known exactly.

The generated quotes are synthetic reference data.

They must never be represented as observed market data.
"""

from __future__ import annotations

import csv

from dataclasses import dataclass
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Iterable, Sequence

from .calendars import BusinessCalendar
from .curves import (
    DiscountFactorCurve,
    SmoothSyntheticZeroCurve,
)
from .instruments import (
    build_ftiie_ois,
)
from .pricing import (
    calculate_par_rate,
)
from .schedules import (
    calculate_effective_date,
)
from .tenors import (
    resolve_contractual_maturity,
)


SYNTHETIC_SCENARIO_ID = (
    "FTIIE_KNOWN_TRUTH_V1"
)


CANONICAL_CALIBRATION_TENORS = (
    "1M",
    "2M",
    "3M",
    "6M",
    "9M",
    "1Y",
    "2Y",
    "3Y",
    "4Y",
    "5Y",
    "7Y",
    "10Y",
    "15Y",
    "20Y",
    "30Y",
)


@dataclass(frozen=True, slots=True)
class SyntheticOISQuote:
    """One synthetic F-TIIE OIS par quote."""

    scenario_id: str

    tenor: str

    trade_date: date
    effective_date: date

    contractual_maturity_date: date
    adjusted_maturity_date: date
    final_payment_date: date

    number_of_periods: int

    par_rate: float

    quote_type: str = "PAR_OIS_RATE"
    data_class: str = "SYNTHETIC_REFERENCE_DATA"

    def __post_init__(self) -> None:
        if not isfinite(self.par_rate):
            raise ValueError(
                "Synthetic par rate must be finite."
            )


def build_synthetic_known_truth_curve(
    reference_date: date,
) -> SmoothSyntheticZeroCurve:
    """Construct canonical synthetic known-truth curve v1.

    Shape
    -----
    The parameterization generates:

        elevated short-end rates
            ↓
        declining medium-term zero rates
            ↓
        moderate long-end normalization

    The shape is intentionally non-flat so that calibration and
    interpolation behavior can be studied.

    It is not intended to reproduce observed Mexican market levels.
    """

    return SmoothSyntheticZeroCurve(
        reference_date=reference_date,

        long_run_rate=0.0720,

        short_spread=0.0060,
        short_decay_years=1.50,

        curvature=-0.0030,
        curvature_decay_years=4.00,
    )


def generate_synthetic_ois_quotes(
    *,
    trade_date: date,
    calendar: BusinessCalendar,
    true_curve: DiscountFactorCurve,
    tenors: Sequence[str] = CANONICAL_CALIBRATION_TENORS,
    notional: float = 1.0,
) -> tuple[SyntheticOISQuote, ...]:
    """Generate par OIS quotes from a known synthetic curve.

    The same known-truth curve is used for projection and discounting,
    consistently with the Core-v1 same-curve assumption.

    The resulting par rates form the market-like observations that will
    later be supplied to the bootstrap engine.

    The bootstrap itself must not access the true curve.
    """

    effective_date = calculate_effective_date(
        trade_date=trade_date,
        calendar=calendar,
    )

    if true_curve.reference_date != effective_date:
        raise ValueError(
            "Synthetic true-curve reference date must equal "
            "the OIS effective date."
        )

    quotes: list[SyntheticOISQuote] = []

    for tenor in tenors:
        maturity_date = resolve_contractual_maturity(
            effective_date=effective_date,
            tenor=tenor,
        )

        # The fixed rate is merely a placeholder during construction.
        # calculate_par_rate() solves the rate implied by the true curve.
        ois = build_ftiie_ois(
            trade_date=trade_date,
            maturity_date=maturity_date,
            fixed_rate=0.0,
            notional=notional,
            calendar=calendar,
        )

        par_rate = calculate_par_rate(
            ois=ois,
            projection_curve=true_curve,
            discount_curve=true_curve,
        )

        quotes.append(
            SyntheticOISQuote(
                scenario_id=SYNTHETIC_SCENARIO_ID,
                tenor=tenor,
                trade_date=trade_date,
                effective_date=ois.effective_date,
                contractual_maturity_date=(
                    ois.contractual_maturity_date
                ),
                adjusted_maturity_date=(
                    ois.adjusted_maturity_date
                ),
                final_payment_date=(
                    ois.final_payment_date
                ),
                number_of_periods=(
                    ois.number_of_periods
                ),
                par_rate=par_rate,
            )
        )

    return tuple(quotes)


def write_synthetic_ois_quotes_csv(
    *,
    quotes: Iterable[SyntheticOISQuote],
    path: str | Path,
) -> None:
    """Write synthetic OIS quotes to deterministic CSV."""

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "scenario_id",
        "data_class",
        "tenor",
        "trade_date",
        "effective_date",
        "contractual_maturity_date",
        "adjusted_maturity_date",
        "final_payment_date",
        "number_of_periods",
        "quote_type",
        "par_rate",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for quote in quotes:
            writer.writerow(
                {
                    "scenario_id": quote.scenario_id,
                    "data_class": quote.data_class,
                    "tenor": quote.tenor,
                    "trade_date": (
                        quote.trade_date.isoformat()
                    ),
                    "effective_date": (
                        quote.effective_date.isoformat()
                    ),
                    "contractual_maturity_date": (
                        quote.contractual_maturity_date.isoformat()
                    ),
                    "adjusted_maturity_date": (
                        quote.adjusted_maturity_date.isoformat()
                    ),
                    "final_payment_date": (
                        quote.final_payment_date.isoformat()
                    ),
                    "number_of_periods": (
                        quote.number_of_periods
                    ),
                    "quote_type": quote.quote_type,
                    "par_rate": (
                        f"{quote.par_rate:.12f}"
                    ),
                }
            )