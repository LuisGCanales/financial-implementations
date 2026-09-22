from datetime import date
from pathlib import Path

import pytest

from yield_curves.bootstrap import (
    bootstrap_ftiie_ois_curve,
)
from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.instruments import (
    build_ftiie_ois,
)
from yield_curves.pricing import (
    calculate_par_rate,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


@pytest.fixture
def quotes():
    return read_synthetic_ois_quotes_csv(
        QUOTES_PATH
    )


@pytest.fixture
def calendar():
    return build_projected_mxmc_calendar(
        start_year=2026,
        end_year=2057,
    )


@pytest.fixture
def bootstrap_result(
    quotes,
    calendar,
):
    return bootstrap_ftiie_ois_curve(
        quotes=quotes,
        calendar=calendar,
    )


def test_bootstrap_creates_one_node_per_quote(
    quotes,
    bootstrap_result,
) -> None:
    assert len(
        bootstrap_result.curve.node_dates
    ) == len(quotes)

    assert len(
        bootstrap_result.steps
    ) == len(quotes)


def test_all_nodes_are_positive(
    bootstrap_result,
) -> None:
    assert all(
        df > 0
        for df in (
            bootstrap_result
            .curve
            .discount_factors
        )
    )


def test_pillar_dates_are_strictly_increasing(
    bootstrap_result,
) -> None:
    dates = (
        bootstrap_result
        .curve
        .node_dates
    )

    assert all(
        later > earlier
        for earlier, later in zip(
            dates,
            dates[1:],
        )
    )


def test_all_solver_steps_converge(
    bootstrap_result,
) -> None:
    assert all(
        step.converged
        for step in bootstrap_result.steps
    )


def test_all_calibration_quotes_reprice(
    bootstrap_result,
) -> None:
    for step in bootstrap_result.steps:
        assert abs(
            step.quote_error_bp
        ) <= 0.01


def test_calibrated_instruments_reprice_from_final_curve(
    quotes,
    calendar,
    bootstrap_result,
) -> None:
    curve = bootstrap_result.curve

    for quote in quotes:
        ois = build_ftiie_ois(
            trade_date=quote.trade_date,
            maturity_date=(
                quote.contractual_maturity_date
            ),
            fixed_rate=quote.par_rate,
            notional=1.0,
            calendar=calendar,
        )

        model_quote = calculate_par_rate(
            ois=ois,
            projection_curve=curve,
            discount_curve=curve,
        )

        error_bp = (
            model_quote
            - quote.par_rate
        ) * 10_000

        assert abs(
            error_bp
        ) <= 0.01


def test_curve_reference_date_matches_effective_date(
    quotes,
    bootstrap_result,
) -> None:
    assert (
        bootstrap_result
        .curve
        .reference_date
        ==
        quotes[0].effective_date
    )


def test_curve_does_not_extend_beyond_last_pillar(
    bootstrap_result,
) -> None:
    curve = bootstrap_result.curve

    with pytest.raises(
        ValueError,
        match="OUT_OF_CURVE_RANGE",
    ):
        curve.discount_factor(
            date(
                curve.last_node_date.year + 1,
                curve.last_node_date.month,
                curve.last_node_date.day,
            )
        )