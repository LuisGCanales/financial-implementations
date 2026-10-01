"""Calendar-day sampling with distinct inclusive and forward-start contracts."""

from collections.abc import Iterator
from datetime import date, timedelta


def inclusive_date_grid(
    *,
    start_date: date,
    end_date: date,
    step_days: int,
) -> tuple[date, ...]:
    """Include both bounds, appending an off-step terminal date exactly once.

    Equal bounds produce one date. Steps are positive calendar days; there
    is no business-day adjustment or conversion through year fractions.
    """
    if step_days <= 0:
        raise ValueError("Grid step must be positive.")
    if end_date < start_date:
        raise ValueError("End date cannot precede start date.")

    dates: list[date] = []
    current = start_date
    while current < end_date:
        dates.append(current)
        current += timedelta(days=step_days)

    if not dates or dates[-1] != end_date:
        dates.append(end_date)
    return tuple(dates)


def iter_forward_start_dates(
    *,
    reference_date: date,
    last_start_date: date,
    grid_step_days: int,
) -> Iterator[date]:
    """Yield regular starts through an already validated last usable start.

    Callers determine ``last_start_date = last_supported_date - period``
    and retain their own period/horizon guards. An off-step last start is
    not appended. Iteration stays lazy so diagnostics evaluates each rate
    before advancing the date, including at the representable date limit.
    """
    if grid_step_days <= 0:
        raise ValueError("Grid step must be positive.")
    if last_start_date < reference_date:
        raise ValueError("Last forward start cannot precede reference date.")

    current = reference_date
    while current <= last_start_date:
        yield current
        current += timedelta(days=grid_step_days)
