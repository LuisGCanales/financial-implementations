"""General F-TIIE OIS CSV inputs and explicit dataset provenance."""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

from .quotes import OISQuote


class QuoteSource(StrEnum):
    SYNTHETIC = "SYNTHETIC_REFERENCE_DATA"
    OBSERVED = "OBSERVED_MARKET_DATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class QuoteProvenance:
    """Declared data nature, separately from its file location and identity."""

    classification: QuoteSource
    source: str
    path: str
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "classification", QuoteSource(self.classification))
        if not self.source.strip():
            raise ValueError("Quote source must not be empty.")


@dataclass(frozen=True, slots=True)
class OISQuoteDataset:
    quotes: tuple[OISQuote, ...]
    provenance: QuoteProvenance


_REQUIRED_COLUMNS = (
    "tenor", "trade_date", "contractual_maturity_date", "par_rate",
)


def _parse_quotes(
    raw: bytes, path: Path, classification: QuoteSource | None
) -> tuple[OISQuote, ...]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: CSV must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    quotes: list[OISQuote] = []
    try:
        columns = reader.fieldnames or []
        if len(columns) != len(set(columns)):
            raise ValueError(f"{path}: duplicate CSV column names.")
        missing = set(_REQUIRED_COLUMNS) - set(columns)
        if missing:
            raise ValueError(f"{path}: missing CSV columns: {', '.join(sorted(missing))}.")
        for row in reader:
            context = f"{path}: line {reader.line_num}"
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{context}: row length does not match the header.")
            values = {key: row[key].strip() for key in _REQUIRED_COLUMNS}
            for key, value in values.items():
                if not value:
                    raise ValueError(f"{context}: '{key}' must not be empty.")
            dates = {}
            for key in ("trade_date", "contractual_maturity_date"):
                try:
                    dates[key] = date.fromisoformat(values[key])
                    if dates[key].isoformat() != values[key]:
                        raise ValueError("Noncanonical date")
                except ValueError as exc:
                    raise ValueError(f"{context}: '{key}' must be a YYYY-MM-DD date.") from exc
            if dates["contractual_maturity_date"] <= dates["trade_date"]:
                raise ValueError(f"{context}: contractual maturity must follow trade date.")
            quote_type = row.get("quote_type", "PAR_OIS_RATE").strip()
            if quote_type != "PAR_OIS_RATE":
                raise ValueError(f"{context}: unsupported quote_type {quote_type!r}.")
            declared_class = row.get("data_class", "").strip()
            if classification is not None and declared_class and declared_class != classification.value:
                raise ValueError(f"{context}: data_class conflicts with declared classification.")
            try:
                quote = OISQuote(
                    tenor=values["tenor"],
                    trade_date=dates["trade_date"],
                    contractual_maturity_date=dates["contractual_maturity_date"],
                    par_rate=float(values["par_rate"]),
                )
            except ValueError as exc:
                raise ValueError(f"{context}: 'par_rate' must be a finite decimal rate.") from exc
            quotes.append(quote)
    except csv.Error as exc:
        raise ValueError(f"{path}: line {reader.line_num}: malformed CSV: {exc}") from exc
    if not quotes:
        raise ValueError(f"{path}: CSV must contain at least one quote.")
    return tuple(quotes)


def read_ois_quotes_csv(path: str | Path) -> tuple[OISQuote, ...]:
    """Read four required columns; preserve input order and decimal rate units.

    Additional columns are allowed, including the frozen synthetic schema.
    Source-specific metadata is not retained by this minimal object reader.
    If quote_type is present it must identify PAR_OIS_RATE.
    """
    path = Path(path)
    return _parse_quotes(path.read_bytes(), path, classification=None)


def load_ois_quote_dataset_csv(
    path: str | Path, *, classification: QuoteSource, source: str
) -> OISQuoteDataset:
    """Load quotes with caller-declared provenance and the exact file fingerprint.

    Classification is never inferred from the filename or directory. A supplied
    data_class column must agree with the declaration. Declaring OBSERVED is a
    caller assertion, not independent verification of market-data authenticity.
    """
    path = Path(path).resolve()
    raw = path.read_bytes()
    provenance = QuoteProvenance(
        classification=classification,
        source=source,
        path=str(path),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    return OISQuoteDataset(
        quotes=_parse_quotes(raw, path, provenance.classification),
        provenance=provenance,
    )
