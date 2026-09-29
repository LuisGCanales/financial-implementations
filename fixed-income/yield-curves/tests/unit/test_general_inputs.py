from dataclasses import replace
from datetime import date
import hashlib
from pathlib import Path

import pytest

from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.calendars import (BusinessCalendar, CalendarCoverageError, CalendarSource, build_mxmc_calendar_from_csv)
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.conventions import BusinessDayConvention
from yield_curves.inputs import validate_calendar_coverage
from yield_curves.quote_io import (
    QuoteSource,
    load_ois_quote_dataset_csv,
    read_ois_quotes_csv,
)
from yield_curves.quotes import OISQuote
from yield_curves.research.synthetic import (read_synthetic_ois_quotes_csv)


HEADER = "tenor,trade_date,contractual_maturity_date,par_rate\n"
ROW = "1M,2026-09-15,2026-10-18,0.08\n"
ROOT = Path(__file__).resolve().parents[2]


def write_csv(tmp_path, text):
    path = tmp_path / "quotes.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_csv_preserves_order_and_decimal_rates(tmp_path):
    path = write_csv(tmp_path, HEADER + ROW + "3M,2026-09-15,2026-12-18,-0.01\n")
    quotes = read_ois_quotes_csv(path)
    assert quotes == (
        OISQuote("1M", date(2026, 9, 15), date(2026, 10, 18), 0.08),
        OISQuote("3M", date(2026, 9, 15), date(2026, 12, 18), -0.01),
    )


def test_zero_rate_bom_and_optional_columns(tmp_path):
    text = "\ufeff" + HEADER.rstrip() + ",note\n" + ROW.rstrip().replace("0.08", "0") + ',"note, with comma"\n'
    quotes = read_ois_quotes_csv(write_csv(tmp_path, text))
    assert quotes[0].par_rate == 0


@pytest.mark.parametrize("text, message", [
    ("", "missing CSV columns"),
    (HEADER, "at least one quote"),
    (HEADER.replace("par_rate", "rate") + ROW, "missing CSV columns"),
    (HEADER.rstrip() + ",tenor\n" + ROW.rstrip() + ",1M\n", "duplicate CSV"),
    (HEADER + ROW.rstrip() + ",extra\n", "line 2.*row length"),
    (HEADER + "1M,2026-09-15,2026-10-18\n", "line 2.*row length"),
    (HEADER + ROW.replace("1M", " "), "line 2.*tenor"),
    (HEADER + ROW.replace("2026-09-15", "20260915"), "line 2.*trade_date"),
    (HEADER + ROW.replace("2026-10-18", "2026-02-30"), "line 2.*contractual_maturity_date"),
    (HEADER + ROW.replace("2026-10-18", "2026-09-15"), "line 2.*maturity must follow"),
    (HEADER + ROW.replace("0.08", "NaN"), "line 2.*finite decimal"),
    (HEADER + ROW.replace("0.08", "inf"), "line 2.*finite decimal"),
    (HEADER + ROW.replace("0.08", "-inf"), "line 2.*finite decimal"),
    (HEADER + ROW.replace("0.08", "8%"), "line 2.*finite decimal"),
    (HEADER + ROW.replace("0.08", ""), "line 2.*par_rate"),
    (HEADER + '"unfinished', "line .*malformed CSV"),
    (HEADER.rstrip() + ",quote_type\n" + ROW.rstrip() + ",ZERO_RATE\n", "line 2.*quote_type"),
])
def test_invalid_csv_reports_schema_or_row_context(tmp_path, text, message):
    with pytest.raises(ValueError, match=message):
        read_ois_quotes_csv(write_csv(tmp_path, text))


def test_general_reader_matches_all_frozen_synthetic_quote_fields():
    path = ROOT / "data/synthetic/ftiie_ois_quotes_v1.csv"
    general = read_ois_quotes_csv(path)
    synthetic = read_synthetic_ois_quotes_csv(path)
    assert general == tuple(
        OISQuote(q.tenor, q.trade_date, q.contractual_maturity_date, q.par_rate)
        for q in synthetic
    )
    assert synthetic[0].scenario_id  # Historical reader still retains its metadata.


def test_provenance_depends_on_declaration_and_content_not_filename(tmp_path):
    path = write_csv(tmp_path, HEADER + ROW)
    copied = tmp_path / "synthetic.csv"
    copied.write_bytes(path.read_bytes())
    datasets = [load_ois_quote_dataset_csv(
        p, classification=QuoteSource.UNKNOWN, source="user supplied"
    ) for p in (path, copied)]
    assert datasets[0].quotes == datasets[1].quotes
    assert datasets[0].provenance.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert datasets[0].provenance.sha256 == datasets[1].provenance.sha256
    assert datasets[0].provenance.path != datasets[1].provenance.path
    assert all(d.provenance.classification is QuoteSource.UNKNOWN for d in datasets)


def test_synthetic_dataset_classification_conflicts_are_rejected():
    path = ROOT / "data/synthetic/ftiie_ois_quotes_v1.csv"
    loaded = load_ois_quote_dataset_csv(
        path, classification=QuoteSource.SYNTHETIC, source="frozen project scenario"
    )
    assert len(loaded.quotes) == 15
    with pytest.raises(ValueError, match="line 2.*data_class conflicts"):
        load_ois_quote_dataset_csv(path, classification=QuoteSource.OBSERVED, source="feed")


def test_provenance_requires_nonempty_source(tmp_path):
    with pytest.raises(ValueError, match="source must not be empty"):
        load_ois_quote_dataset_csv(
            write_csv(tmp_path, HEADER + ROW), classification=QuoteSource.UNKNOWN, source=" "
        )


def test_coverage_requires_both_bounds_in_order():
    with pytest.raises(ValueError, match="both start and end"):
        BusinessCalendar("test", coverage_start=date(2026, 1, 1))
    with pytest.raises(ValueError, match="cannot precede"):
        BusinessCalendar("test", coverage_start=date(2026, 2, 1), coverage_end=date(2026, 1, 1))


@pytest.mark.parametrize("operation", [
    lambda c, d: c.is_business_day(d),
    lambda c, d: c.is_holiday(d),
    lambda c, d: c.is_weekend(d),
    lambda c, d: c.adjust(d, BusinessDayConvention.NONE),
    lambda c, d: c.add_business_days(d, 0),
    lambda c, d: c.following(d),
    lambda c, d: c.preceding(d),
])
def test_declared_coverage_is_enforced_for_date_operations(operation):
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    with pytest.raises(CalendarCoverageError, match="outside calendar coverage"):
        operation(calendar, date(2027, 1, 2))  # Even weekends outside coverage fail.


def test_calendar_iteration_cannot_cross_declared_coverage():
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    calendar.require_coverage(date(2026, 1, 1), date(2026, 12, 31))
    assert calendar.provenance.kind is CalendarSource.PROJECTED
    with pytest.raises(CalendarCoverageError):
        calendar.add_business_days(date(2026, 12, 31), 1)
    with pytest.raises(CalendarCoverageError):
        calendar.preceding(date(2026, 1, 1))


def test_holiday_csv_preserves_declared_coverage_and_provenance(tmp_path):
    path = tmp_path / "holidays.csv"
    path.write_text("date,name\n2026-09-16,Holiday\n")
    calendar = build_mxmc_calendar_from_csv(
        path, coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31),
        source="provided fixture",
    )
    assert calendar.coverage_start == date(2026, 1, 1)
    assert calendar.provenance.kind is CalendarSource.PROVIDED
    assert calendar.provenance.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert calendar.is_business_day(date(2026, 1, 2))
    assert not calendar.is_business_day(date(2026, 9, 16))
    # No coverage inferred from the minimum/maximum holiday dates.
    unspecified = build_mxmc_calendar_from_csv(path)
    with pytest.raises(CalendarCoverageError, match="unspecified"):
        unspecified.require_coverage(date(2026, 9, 16))


def test_operational_coverage_check_rejects_unspecified_legacy_calendar():
    calendar = BusinessCalendar("WEEKENDS_ONLY")
    assert calendar.is_business_day(date(2026, 9, 15))
    quote = OISQuote("1M", date(2026, 9, 15), date(2026, 10, 18), 0.08)
    with pytest.raises(CalendarCoverageError, match="Quote 1M.*unspecified"):
        validate_calendar_coverage(quotes=(quote,), calendar=calendar)


def test_coverage_check_includes_payment_lag_after_contractual_maturity():
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    calendar = replace(calendar, coverage_end=date(2026, 10, 19))
    quote = OISQuote("1M", date(2026, 9, 15), date(2026, 10, 18), 0.08)
    calendar.require_coverage(quote.trade_date, quote.contractual_maturity_date)
    with pytest.raises(CalendarCoverageError, match="Quote 1M.*outside calendar coverage"):
        validate_calendar_coverage(quotes=(quote,), calendar=calendar)


def test_general_csv_and_bounded_calendar_build_an_accepted_baseline(tmp_path):
    path = write_csv(tmp_path, HEADER + ROW + "3M,2026-09-15,2026-12-18,0.081\n")
    dataset = load_ois_quote_dataset_csv(
        path, classification=QuoteSource.SYNTHETIC, source="integration test scenario"
    )
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    validate_calendar_coverage(quotes=dataset.quotes, calendar=calendar)
    result = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar)
    assert result.accepted_for_use
    assert len(result.acceptance.checks) == 2


def test_baseline_construction_rejects_dates_outside_declared_coverage(tmp_path):
    quotes = read_ois_quotes_csv(write_csv(
        tmp_path, HEADER + ROW + "3M,2026-09-15,2026-12-18,0.081\n"
    ))
    calendar = build_projected_mxmc_calendar(start_year=2025, end_year=2025)
    with pytest.raises(CalendarCoverageError, match="outside calendar coverage"):
        build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)
