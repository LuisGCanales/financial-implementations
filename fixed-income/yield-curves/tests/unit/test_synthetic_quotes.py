from datetime import date

import pytest

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.instruments import (
    build_ftiie_ois,
)
from yield_curves.pricing import (
    value_ftiie_ois,
)
from yield_curves.schedules import (
    calculate_effective_date,
)
from yield_curves.synthetic import (
    CANONICAL_CALIBRATION_TENORS,
    build_synthetic_known_truth_curve,
    generate_synthetic_ois_quotes,
)


TRADE_DATE = date(
    2026,
    9,
    15,
)


@pytest.fixture
def calendar():
    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture
def true_curve(calendar):
    effective_date = calculate_effective_date(
        TRADE_DATE,
        calendar,
    )

    return build_synthetic_known_truth_curve(
        effective_date
    )


@pytest.fixture
def synthetic_quotes(
    calendar,
    true_curve,
):
    return generate_synthetic_ois_quotes(
        trade_date=TRADE_DATE,
        calendar=calendar,
        true_curve=true_curve,
    )


def test_all_canonical_tenors_are_generated(
    synthetic_quotes,
) -> None:
    assert len(
        synthetic_quotes
    ) == len(
        CANONICAL_CALIBRATION_TENORS
    )

    assert tuple(
        quote.tenor
        for quote in synthetic_quotes
    ) == CANONICAL_CALIBRATION_TENORS


def test_all_quotes_are_explicitly_synthetic(
    synthetic_quotes,
) -> None:
    assert all(
        quote.data_class
        == "SYNTHETIC_REFERENCE_DATA"
        for quote in synthetic_quotes
    )


def test_all_quotes_share_effective_date(
    synthetic_quotes,
) -> None:
    effective_dates = {
        quote.effective_date
        for quote in synthetic_quotes
    }

    assert effective_dates == {
        date(2026, 9, 18)
    }


def test_synthetic_quotes_are_finite_and_positive(
    synthetic_quotes,
) -> None:
    assert all(
        quote.par_rate > 0
        for quote in synthetic_quotes
    )


def test_synthetic_quotes_are_not_flat(
    synthetic_quotes,
) -> None:
    rounded_quotes = {
        round(
            quote.par_rate,
            8,
        )
        for quote in synthetic_quotes
    }

    assert len(rounded_quotes) > 1


def test_each_synthetic_quote_reprices_to_zero(
    calendar,
    true_curve,
    synthetic_quotes,
) -> None:
    for quote in synthetic_quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        valuation = value_ftiie_ois(
            ois=ois,
            projection_curve=true_curve,
            discount_curve=true_curve,
        )

        assert (
            valuation.npv_receive_float_pay_fixed
            == pytest.approx(
                0.0,
                abs=1e-10,
            )
        )


def test_quote_maturities_are_strictly_increasing(
    synthetic_quotes,
) -> None:
    maturities = [
        quote.contractual_maturity_date
        for quote in synthetic_quotes
    ]

    assert all(
        later > earlier
        for earlier, later in zip(
            maturities,
            maturities[1:],
        )
    )


def test_final_payment_is_not_before_maturity(
    synthetic_quotes,
) -> None:
    assert all(
        quote.final_payment_date
        >= quote.adjusted_maturity_date
        for quote in synthetic_quotes
    )


def test_mismatched_curve_reference_date_is_rejected(
    calendar,
) -> None:
    wrong_curve = (
        build_synthetic_known_truth_curve(
            date(2026, 9, 21)
        )
    )

    with pytest.raises(
        ValueError,
        match="reference date",
    ):
        generate_synthetic_ois_quotes(
            trade_date=TRADE_DATE,
            calendar=calendar,
            true_curve=wrong_curve,
        )