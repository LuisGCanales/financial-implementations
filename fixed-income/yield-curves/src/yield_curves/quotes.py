"""Shared F-TIIE OIS quote contract and general in-memory representation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Protocol


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
