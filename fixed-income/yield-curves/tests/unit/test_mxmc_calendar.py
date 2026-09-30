from datetime import date
from pathlib import Path
import hashlib

import pytest

from yield_curves.calendar_io import build_mxmc_calendar_from_csv, load_holidays_csv
from yield_curves.calendars import BusinessCalendar, CalendarProvenance, CalendarSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MXMC_2026_PATH = (
    PROJECT_ROOT
    / "data"
    / "calendars"
    / "mxmc_2026.csv"
)


def test_mxmc_2026_loads() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.name == "MXMC"


def test_independence_day_is_holiday() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert not calendar.is_business_day(
        date(2026, 9, 16)
    )


def test_days_around_independence_day() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.is_business_day(
        date(2026, 9, 15)
    )

    assert not calendar.is_business_day(
        date(2026, 9, 16)
    )

    assert calendar.is_business_day(
        date(2026, 9, 17)
    )


def test_bmv_cnbv_bank_employee_day_is_holiday() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    assert calendar.is_holiday(
        date(2026, 12, 12)
    )


def test_t_plus_two_skips_independence_day() -> None:
    calendar = build_mxmc_calendar_from_csv(
        MXMC_2026_PATH
    )

    trade_date = date(2026, 9, 15)

    result = calendar.add_business_days(
        trade_date,
        2,
    )

    # 16-Sep is a holiday.
    # 17-Sep = T+1
    # 18-Sep = T+2
    assert result == date(2026, 9, 18)


@pytest.mark.parametrize("raw", [
    b"date,label\n2026-09-16,Holiday\n2026-01-01,New year\n2026-09-16,Duplicate\n ,Blank\n",
    b"\xef\xbb\xbfdate,label\r\n2026-09-16,Holiday\r\n2026-01-01,New year\r\n2026-09-16,Duplicate\r\n ,Blank\r\n",
])
@pytest.mark.parametrize("source", [None, "declared source"])
def test_csv_preserves_calendar_values_and_raw_byte_provenance(tmp_path, raw, source):
    path = tmp_path / "holidays.csv"
    path.write_bytes(raw)
    expected = BusinessCalendar(
        name="MXMC",
        holidays=frozenset({date(2026, 1, 1), date(2026, 9, 16)}),
        weekend_days=frozenset({5, 6}),
        coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 12, 31),
        provenance=CalendarProvenance(
            source=str(path.resolve()) if source is None else source,
            kind=CalendarSource.PROVIDED,
            sha256=hashlib.sha256(raw).hexdigest(),
        ),
    )
    assert load_holidays_csv(str(path)) == expected.holidays
    assert build_mxmc_calendar_from_csv(
        path, coverage_start=expected.coverage_start,
        coverage_end=expected.coverage_end, source=source,
    ) == expected


def test_checksum_tracks_file_bytes_even_when_calendar_values_match(tmp_path):
    path = tmp_path / "holidays.csv"
    path.write_bytes(b"date\n2026-09-16\n")
    first = build_mxmc_calendar_from_csv(path)
    path.write_bytes(b"\xef\xbb\xbfdate\r\n2026-09-16\r\n")
    second = build_mxmc_calendar_from_csv(path)
    assert first.holidays == second.holidays
    assert first.provenance.source == second.provenance.source
    assert first.provenance.sha256 != second.provenance.sha256
    assert first.coverage_start is first.coverage_end is None


def test_holiday_loader_supports_explicit_date_column(tmp_path):
    path = tmp_path / "holidays.csv"
    path.write_text("holiday,note\n 2026-09-16 ,independence\n", encoding="utf-8")
    assert load_holidays_csv(path, date_column="holiday") == frozenset({date(2026, 9, 16)})


@pytest.mark.parametrize("loader", [load_holidays_csv, build_mxmc_calendar_from_csv])
@pytest.mark.parametrize("text,message", [
    ("other\n2026-09-16\n", "CSV must contain column 'date'"),
    ("date\nnot-a-date\n", "Invalid isoformat"),
])
def test_csv_errors_remain_useful(tmp_path, loader, text, message):
    path = tmp_path / "holidays.csv"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        loader(path)


@pytest.mark.parametrize("loader", [load_holidays_csv, build_mxmc_calendar_from_csv])
def test_missing_calendar_file_raises(tmp_path, loader):
    with pytest.raises(FileNotFoundError):
        loader(tmp_path / "missing.csv")
