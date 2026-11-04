"""Read relocated evidence without running experiments or generating artifacts."""

import hashlib
import importlib.util
from datetime import date
from pathlib import Path
from shutil import copyfile

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SENSITIVITY = ROOT / "scripts/experiments/sensitivity"


def load_reader(filename):
    """Import the actual script without entering its guarded main()."""
    path = SENSITIVITY / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_hash(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


@pytest.mark.parametrize("filename", [
    "plot_global_forward_sensitivity_heatmaps.py",
    "report_forward_sensitivity_locality.py",
])
def test_sensitivity_readers_open_relocated_evidence(filename, tmp_path):
    reader = load_reader(filename)
    relative_paths = tuple(
        Path("tables/07_global_sensitivity") / name
        for name in (
            "global_forward_sensitivity_dense.csv",
            "global_node_sensitivity_long.csv",
        )
    )
    source_paths = reader.sensitivity_data_paths()
    assert source_paths == tuple(ROOT / "outputs/research" / p for p in relative_paths)
    assert all(path.is_file() for path in source_paths)
    source_hashes = tuple(file_hash(path) for path in source_paths)

    relocated_paths = tuple(tmp_path / p for p in relative_paths)
    relocated_paths[0].parent.mkdir(parents=True)
    for source, destination in zip(source_paths, relocated_paths):
        copyfile(source, destination)
    assert reader.sensitivity_data_paths(reports_root=tmp_path) == relocated_paths
    assert tuple(file_hash(path) for path in relocated_paths) == source_hashes

    if filename == "plot_global_forward_sensitivity_heatmaps.py":
        reference_date, scenario, data = reader.read_dense_forward_sensitivity(
            reports_root=tmp_path,
        )
        assert set(data) == {
            "LOG_LINEAR_DF", "LINEAR_CONTINUOUS_ZERO", "CUBIC_CONTINUOUS_ZERO",
        }
        pillars = reader.read_pillar_years(
            reference_date=reference_date, reports_root=tmp_path,
        )
        assert pillars
        assert all(np.isfinite(year) and year > 0 for year in pillars.values())
        for method_data in data.values():
            matrix = method_data["matrix"]
            assert matrix.size > 0
            assert matrix.shape == (
                len(method_data["shock_indices"]), len(method_data["forward_dates"]),
            )
            assert np.isfinite(matrix).all()
            assert len(method_data["shock_labels"]) == matrix.shape[0]
            assert set(pillars) == set(method_data["shock_indices"])
    else:
        scenario, reference_date, results = reader.load_locality_results(
            reports_root=tmp_path,
        )
        assert results
        assert all(item["scenario"] == scenario for item in results)
        assert all(item["reference_date"] == reference_date for item in results)
        assert all(item["locality"].observation_count > 0 for item in results)

    assert scenario == "FTIIE_KNOWN_TRUTH_V1"
    assert reference_date == date(2026, 9, 18)
    assert tuple(file_hash(path) for path in source_paths) == source_hashes
    assert tuple(file_hash(path) for path in relocated_paths) == source_hashes
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == set(relocated_paths)
    # Empty explicit roots (forward, pillar, locality and missing node input)
    # are covered by test_experiment_reports_root.py's no-fallback tests.
