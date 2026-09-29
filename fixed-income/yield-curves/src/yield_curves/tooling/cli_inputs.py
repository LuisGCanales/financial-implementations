"""Explicit input arguments shared by local operational and assurance tools."""

from datetime import date
from pathlib import Path

from ..calendars import build_mxmc_calendar_from_csv
from ..quote_io import QuoteSource, load_ois_quote_dataset_csv


def add_input_arguments(parser):
    parser.add_argument("--quotes", type=Path, required=True)
    parser.add_argument("--classification", type=QuoteSource, choices=list(QuoteSource), required=True)
    parser.add_argument("--source", required=True, help="Quote dataset source description.")
    parser.add_argument("--calendar", type=Path, required=True, help="Holiday CSV with a date column.")
    parser.add_argument("--calendar-start", type=date.fromisoformat, required=True)
    parser.add_argument("--calendar-end", type=date.fromisoformat, required=True)
    parser.add_argument("--calendar-source", required=True)


def load_cli_inputs(args):
    dataset = load_ois_quote_dataset_csv(
        args.quotes, classification=args.classification, source=args.source,
    )
    calendar = build_mxmc_calendar_from_csv(
        args.calendar, coverage_start=args.calendar_start, coverage_end=args.calendar_end,
        source=args.calendar_source,
    )
    return dataset, calendar


def print_acceptance(acceptance):
    print(f"solver_success: {acceptance.calibration_success}")
    print(f"accepted_for_use: {acceptance.accepted_for_use}")
    print(f"quote_count: {len(acceptance.checks)}")
    print(f"max_abs_repricing_error_bp: {acceptance.max_abs_repricing_error_bp:.12g}")
    for issue in acceptance.issues:
        print(f"issue: {issue}")
