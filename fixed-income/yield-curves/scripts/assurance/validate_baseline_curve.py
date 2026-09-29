"""Rebuild explicit inputs or reassess the persisted current baseline without publishing."""

import argparse
from pathlib import Path

from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.tooling.cli_inputs import (add_input_arguments, load_cli_inputs, print_acceptance)
from yield_curves.snapshot_assurance import assess_current_snapshot


def _parse_args(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    rebuild = modes.add_parser("rebuild", help="Calibrate explicit inputs; do not export or publish.")
    add_input_arguments(rebuild)
    snapshot = modes.add_parser("snapshot", help="Verify and reprice persisted nodes; no solver.")
    snapshot.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args(arguments)


def main(arguments=None):
    args = _parse_args(arguments)
    if args.mode == "snapshot":
        acceptance = assess_current_snapshot(args.output_root)
    else:
        dataset, calendar = load_cli_inputs(args)
        acceptance = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar).acceptance
    print(f"validation_mode: {args.mode}")
    print_acceptance(acceptance)
    return 0 if acceptance.accepted_for_use else 1


if __name__ == "__main__":
    raise SystemExit(main())
