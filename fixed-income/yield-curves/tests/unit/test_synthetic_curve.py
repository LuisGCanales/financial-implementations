from datetime import date

import pytest

from yield_curves.synthetic import (
    build_synthetic_known_truth_curve,
)
from yield_curves.tenors import (
    resolve_contractual_maturity,
)


REFERENCE_DATE = date(
    2026,
    9,
    18,
)


def test_reference_discount_factor_is_one() -> None:
    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    assert curve.discount_factor(
        REFERENCE_DATE
    ) == pytest.approx(1.0)


def test_synthetic_curve_is_non_flat() -> None:
    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    one_month = resolve_contractual_maturity(
        effective_date=REFERENCE_DATE,
        tenor="1M",
    )

    five_year = resolve_contractual_maturity(
        effective_date=REFERENCE_DATE,
        tenor="5Y",
    )

    thirty_year = resolve_contractual_maturity(
        effective_date=REFERENCE_DATE,
        tenor="30Y",
    )

    short_rate = curve.zero_rate(
        one_month
    )

    medium_rate = curve.zero_rate(
        five_year
    )

    long_rate = curve.zero_rate(
        thirty_year
    )

    assert medium_rate < short_rate
    assert long_rate > medium_rate


def test_selected_discount_factors_are_positive_and_decreasing() -> None:
    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    dates = [
        REFERENCE_DATE,
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="1M",
        ),
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="1Y",
        ),
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="5Y",
        ),
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="10Y",
        ),
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="30Y",
        ),
    ]

    discount_factors = [
        curve.discount_factor(target)
        for target in dates
    ]

    assert all(
        value > 0
        for value in discount_factors
    )

    assert all(
        later < earlier
        for earlier, later in zip(
            discount_factors,
            discount_factors[1:],
        )
    )


def test_short_and_long_zero_rates_are_reasonable_for_scenario() -> None:
    curve = build_synthetic_known_truth_curve(
        REFERENCE_DATE
    )

    short = curve.zero_rate(
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="1M",
        )
    )

    long = curve.zero_rate(
        resolve_contractual_maturity(
            effective_date=REFERENCE_DATE,
            tenor="30Y",
        )
    )

    # Scenario-level sanity checks, not market assertions.
    assert 0.07 < short < 0.08
    assert 0.07 < long < 0.075