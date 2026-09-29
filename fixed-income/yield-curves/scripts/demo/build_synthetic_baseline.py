"""Explicit synthetic baseline demo with a projected 2026–2057 calendar."""

import argparse
from pathlib import Path

from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.tooling.cli_inputs import (print_acceptance)
from yield_curves.tooling.project_paths import (find_project_root)
from yield_curves.quote_io import QuoteSource, load_ois_quote_dataset_csv
from yield_curves.snapshots import export_baseline_snapshot


PROJECT_ROOT = find_project_root(Path(__file__))


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "outputs/demo/baseline")
    args = parser.parse_args(arguments)
    dataset = load_ois_quote_dataset_csv(
        PROJECT_ROOT / "data/synthetic/ftiie_ois_quotes_v1.csv",
        classification=QuoteSource.SYNTHETIC, source="Frozen F-TIIE synthetic reference scenario",
    )
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2057)
    result = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar)
    exported = export_baseline_snapshot(result=result, dataset=dataset, calendar=calendar,
                                        output_root=args.output_root)
    print_acceptance(result.acceptance)
    print(f"run_path: {exported.run_path}")
    return 0 if result.accepted_for_use else 1


if __name__ == "__main__":
    raise SystemExit(main())
