"""Build and publish a baseline using explicitly supplied inputs."""

import argparse
from pathlib import Path

from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.tooling.cli_inputs import (add_input_arguments, load_cli_inputs, print_acceptance)
from yield_curves.snapshots import export_baseline_snapshot


def build_snapshot(*, dataset, calendar, output_root):
    """Build and archive using the exact dataset and calendar supplied by the caller."""
    result = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar)
    export_baseline_snapshot(result=result, dataset=dataset, calendar=calendar,
                             output_root=output_root)
    return result


def _parse_args(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_arguments(parser)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args(arguments)


def main(arguments=None):
    args = _parse_args(arguments)
    dataset, calendar = load_cli_inputs(args)
    result = build_snapshot(dataset=dataset, calendar=calendar, output_root=args.output_root)
    print_acceptance(result.acceptance)
    print(f"output_root: {args.output_root.resolve()}")
    print(f"published_current: {result.accepted_for_use}")
    return 0 if result.accepted_for_use else 1


if __name__ == "__main__":
    raise SystemExit(main())
