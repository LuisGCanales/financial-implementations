from datetime import date

import pytest

from yield_curves.tenors import (
    Tenor,
    TenorUnit,
    add_calendar_months,
    parse_tenor,
    resolve_contractual_maturity,
)


def test_parse_month_tenor() -> None:
    tenor = parse_tenor("3M")

    assert tenor == Tenor(
        count=3,
        unit=TenorUnit.MONTH,
    )


def test_parse_year_tenor() -> None:
    tenor = parse_tenor("10Y")

    assert tenor == Tenor(
        count=10,
        unit=TenorUnit.YEAR,
    )


def test_tenor_is_case_insensitive() -> None:
    assert parse_tenor(
        "5y"
    ) == Tenor(
        count=5,
        unit=TenorUnit.YEAR,
    )


def test_invalid_tenor_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_tenor("ABC")


def test_zero_tenor_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        parse_tenor("0M")


def test_calendar_month_addition() -> None:
    assert add_calendar_months(
        date(2026, 9, 18),
        1,
    ) == date(
        2026,
        10,
        18,
    )


def test_month_end_is_clipped() -> None:
    assert add_calendar_months(
        date(2026, 1, 31),
        1,
    ) == date(
        2026,
        2,
        28,
    )


def test_leap_day_plus_one_year() -> None:
    assert add_calendar_months(
        date(2024, 2, 29),
        12,
    ) == date(
        2025,
        2,
        28,
    )


def test_resolve_one_year_maturity() -> None:
    effective = date(
        2026,
        9,
        18,
    )

    maturity = resolve_contractual_maturity(
        effective_date=effective,
        tenor="1Y",
    )

    assert maturity == date(
        2027,
        9,
        18,
    )


def test_resolve_thirty_year_maturity() -> None:
    effective = date(
        2026,
        9,
        18,
    )

    maturity = resolve_contractual_maturity(
        effective_date=effective,
        tenor="30Y",
    )

    assert maturity == date(
        2056,
        9,
        18,
    )