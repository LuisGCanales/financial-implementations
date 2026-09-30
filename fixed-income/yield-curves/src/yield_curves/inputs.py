"""Input preparation checks reusable by operational entrypoints."""

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Sequence

from .calendars import BusinessCalendar, CalendarCoverageError
from .instruments import FTiieOIS, build_calibration_ftiie_ois
from .quotes import OISCalibrationQuote, OISQuote


def validate_calendar_coverage(
    *, quotes: Sequence[OISCalibrationQuote], calendar: BusinessCalendar
) -> None:
    """Require declared coverage for all dates used to construct the input OIS.

    Reconstructing instruments checks adjusted maturities, payment lags and
    overnight observations through the calendar's date operations. Checking only
    the contractual maturity would miss those dates. This is an input check,
    not a verification of the supplied holiday source or a curve acceptance test.
    """
    if not quotes:
        raise ValueError("At least one quote is required for calendar coverage checks.")
    for quote in quotes:
        _build_covered_instrument(quote, calendar)


def _build_covered_instrument(
    quote: OISCalibrationQuote, calendar: BusinessCalendar
) -> FTiieOIS:
    try:
        calendar.require_coverage(quote.trade_date, quote.contractual_maturity_date)
        instrument = build_calibration_ftiie_ois(quote=quote, calendar=calendar)
        calendar.require_coverage(quote.trade_date, instrument.last_relevant_date)
        return instrument
    except CalendarCoverageError as exc:
        raise CalendarCoverageError(f"Quote {quote.tenor}: {exc}") from exc


class BaselineInputError(ValueError):
    """Invalid operational quote set, with machine-readable issue codes."""

    def __init__(self, issues: Sequence[str]):
        self.issues = tuple(issues)
        super().__init__("Invalid baseline inputs: " + ", ".join(self.issues))


@dataclass(frozen=True, slots=True)
class CalendarFinancialIdentity:
    """Complete calendar values, independent of file/source declarations."""

    name: str
    coverage_start: date | None
    coverage_end: date | None
    weekend_days: tuple[int, ...]
    holidays: tuple[date, ...]

    @classmethod
    def capture(cls, calendar: BusinessCalendar) -> "CalendarFinancialIdentity":
        return cls(
            str(calendar.name), calendar.coverage_start, calendar.coverage_end,
            tuple(sorted(calendar.weekend_days)), tuple(sorted(calendar.holidays)),
        )

    def to_calendar(self) -> BusinessCalendar:
        """Use only the captured financial values for date operations."""
        return BusinessCalendar(
            name=self.name, coverage_start=self.coverage_start,
            coverage_end=self.coverage_end, weekend_days=frozenset(self.weekend_days),
            holidays=frozenset(self.holidays),
        )


@dataclass(frozen=True, slots=True)
class PreparedBaselineInputs:
    """Validated quote ordering and expected curve geometry."""

    quotes: tuple[OISQuote, ...]
    reference_date: date
    pillar_dates: tuple[date, ...]
    calendar: CalendarFinancialIdentity


def prepare_baseline_inputs(
    *, quotes: Sequence[OISCalibrationQuote], calendar: BusinessCalendar
) -> PreparedBaselineInputs:
    """Validate operational inputs before solving or assessing a baseline.

    Requires two or more quotes for the cubic representation and declared
    calendar coverage. Source authenticity is outside this input contract.
    """
    quotes = tuple(quotes)
    calendar_identity = CalendarFinancialIdentity.capture(calendar)
    calendar = calendar_identity.to_calendar()
    captured_quotes: list[OISQuote] = []
    issues: list[str] = []
    if not quotes:
        raise BaselineInputError(("EMPTY_QUOTE_SET",))
    if len(quotes) < 2:
        issues.append("INSUFFICIENT_QUOTES_FOR_CUBIC")
    tenors: set[str] = set()
    maturities: set[date] = set()
    trade_dates: set[date] = set()
    previous_maturity = None
    for index, quote in enumerate(quotes):
        label = f"quote[{index}]"
        tenor = getattr(quote, "tenor", None)
        if not isinstance(tenor, str) or not tenor.strip():
            issues.append(f"INVALID_TENOR:{label}")
        else:
            if tenor in tenors:
                issues.append(f"DUPLICATE_TENOR:{tenor}")
            tenors.add(tenor)
            label = tenor
        trade = getattr(quote, "trade_date", None)
        maturity = getattr(quote, "contractual_maturity_date", None)
        if type(trade) is not date or type(maturity) is not date:
            issues.append(f"INVALID_QUOTE_DATE:{label}")
        else:
            trade_dates.add(trade)
            if maturity <= trade:
                issues.append(f"INVALID_MATURITY:{label}")
            if maturity in maturities:
                issues.append(f"DUPLICATE_MATURITY:{label}")
            if previous_maturity is not None and maturity <= previous_maturity:
                issues.append(f"NON_INCREASING_MATURITY:{label}")
            maturities.add(maturity)
            previous_maturity = maturity
        rate = getattr(quote, "par_rate", None)
        try:
            finite = not isinstance(rate, bool) and isfinite(rate)
        except (TypeError, ValueError, OverflowError):
            finite = False
        if not finite:
            issues.append(f"NON_FINITE_OR_INVALID_QUOTE:{label}")
        if not issues:
            captured_quotes.append(OISQuote(str(tenor), trade, maturity, float(rate)))
    if len(trade_dates) > 1:
        issues.append("MULTIPLE_TRADE_DATES")
    if issues:
        raise BaselineInputError(issues)

    quotes = tuple(captured_quotes)
    reference_date = None
    pillar_dates: list[date] = []
    for quote in quotes:
        try:
            instrument = _build_covered_instrument(quote, calendar)
        except CalendarCoverageError:
            raise
        except ValueError as exc:
            raise BaselineInputError((f"INVALID_INSTRUMENT:{quote.tenor}",)) from exc
        if reference_date is None:
            reference_date = instrument.effective_date
        elif instrument.effective_date != reference_date:
            raise BaselineInputError(("REFERENCE_DATE_MISMATCH_BETWEEN_QUOTES",))
        pillar = instrument.final_payment_date
        if pillar_dates and pillar <= pillar_dates[-1]:
            raise BaselineInputError((f"NON_INCREASING_PILLAR:{quote.tenor}",))
        pillar_dates.append(pillar)

    assert reference_date is not None
    return PreparedBaselineInputs(
        quotes, reference_date, tuple(pillar_dates), calendar_identity
    )
