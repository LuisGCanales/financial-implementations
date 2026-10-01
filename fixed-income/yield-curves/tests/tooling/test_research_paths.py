"""Read relocated evidence without running experiments or generating artifacts."""

import ast
import csv
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SENSITIVITY = ROOT / "scripts/experiments/sensitivity"


def load_reader_definitions(filename):
    """Load only read helpers and their dependencies; never execute script main."""
    path = SENSITIVITY / filename
    tree = ast.parse(path.read_text())
    names = {"REPORT_SECTION", "FORWARD_DATA_PATH", "NODE_DATA_PATH", "METHODS"}
    helpers = {"read_csv_rows", "read_dense_forward_sensitivity", "read_pillar_years", "act_360"}
    nodes = [node for node in tree.body if (
        isinstance(node, ast.ImportFrom) and node.module in {"datetime", "yield_curves.date_grids"}
        or isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names for target in node.targets
        )
        or isinstance(node, ast.FunctionDef) and node.name in helpers
    )]
    namespace = {"PROJECT_ROOT": ROOT, "Path": Path, "csv": csv, "np": np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("filename", [
    "plot_global_forward_sensitivity_heatmaps.py",
    "report_forward_sensitivity_locality.py",
])
def test_sensitivity_readers_open_relocated_evidence(filename):
    reader = load_reader_definitions(filename)
    for name in ("FORWARD_DATA_PATH", "NODE_DATA_PATH"):
        assert reader[name].is_relative_to(ROOT / "outputs/research/tables")
        assert reader[name].is_file()
    if "read_csv_rows" in reader:
        for name in ("FORWARD_DATA_PATH", "NODE_DATA_PATH"):
            assert reader["read_csv_rows"](reader[name])
    else:
        reference_date, scenario, data = reader["read_dense_forward_sensitivity"]()
        assert scenario
        assert len(data) == 3
        assert reader["read_pillar_years"](reference_date=reference_date)
