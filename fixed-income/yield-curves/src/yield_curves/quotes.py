"""Shared F-TIIE OIS quote contract and general in-memory representation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Protocol, Sequence


class OISCalibrationQuote(Protocol):
    """Attributes consumed by calibration and repricing, regardless of source."""

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float


@dataclass(frozen=True, slots=True)
class OISQuote:
    """One F-TIIE OIS par quote; rates use decimal units (0.08 means 8%).

    Calendar-derived dates are reconstructed by instrument construction.
    Source metadata belongs to the input dataset, rather than this contract.
    Negative and zero rates are supported.
    """

    tenor: str
    trade_date: date
    contractual_maturity_date: date
    par_rate: float

    def __post_init__(self) -> None:
        if not isfinite(self.par_rate):
            raise ValueError("OIS par rate must be finite.")


def bump_ois_quotes(
    *,
    quotes: Sequence[OISCalibrationQuote],
    shock_index: int,
    bump_bp: float,
) -> tuple[OISQuote, ...]:
    """Copy financial values, changing only the selected rate by signed bp.

    Selection and experiment metadata belong to the caller. Zero is a no-op;
    negative bumps are supported. Tenors and dates are copied without
    normalization; validation remains at the existing consumer boundaries.
    """
    if not 0 <= shock_index < len(quotes):
        raise IndexError("Shock index is outside quote set.")

    bump_rate = bump_bp / 10_000.0
    return tuple(
        OISQuote(
            tenor=quote.tenor,
            trade_date=quote.trade_date,
            contractual_maturity_date=quote.contractual_maturity_date,
            par_rate=(
                quote.par_rate + bump_rate
                if index == shock_index else quote.par_rate
            ),
        )
        for index, quote in enumerate(quotes)
    )
