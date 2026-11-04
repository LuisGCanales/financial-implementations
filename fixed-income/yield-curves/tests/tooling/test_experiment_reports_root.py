"""Regression coverage for experiment destinations and persisted-data readers."""

import importlib.util
import inspect
import json
from datetime import date
from pathlib import Path
import runpy
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from yield_curves.tooling import reporting


PROJECT = Path(__file__).resolve().parents[2]
EXPERIMENTS = PROJECT / "scripts" / "experiments"
PRODUCERS = (
    "bootstrap/bootstrap_synthetic_reference_data.py",
    "bootstrap/plot_bootstrap_recovery.py",
    "bootstrap/report_bootstrap_recovery_metrics.py",
    "bootstrap/report_central_quote_sensitivity.py",
    "bootstrap/report_curve_diagnostics.py",
    "bootstrap/report_quote_sensitivity.py",
    "bootstrap/validate_synthetic_bootstrap.py",
    "interpolation/compare_three_interpolation_methods.py",
    "interpolation/plot_interpolation_method_comparison.py",
    "interpolation/plot_three_interpolation_methods.py",
    "sensitivity/report_global_sensitivity.py",
    "sensitivity/plot_global_forward_sensitivity_heatmaps.py",
    "sensitivity/report_forward_sensitivity_locality.py",
    "synthetic/plot_synthetic_reference_data.py",
)


def load_script(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, EXPERIMENTS / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("relative", PRODUCERS)
def test_report_entrypoints_accept_optional_root(relative, monkeypatch, capsys):
    module = load_script(relative)
    parameter = inspect.signature(module.main).parameters["reports_root"]
    assert parameter.default is None
    assert parameter.kind == inspect.Parameter.KEYWORD_ONLY
    monkeypatch.setattr(sys, "argv", [str(EXPERIMENTS / relative), "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(EXPERIMENTS / relative), run_name="__main__")
    assert exc.value.code == 0
    assert "--reports-root" in capsys.readouterr().out


@pytest.mark.parametrize("category,suffix", [
    ("tables", "csv"), ("figures", "png"), ("figures", "svg"),
    ("text", "txt"), ("metadata", "json"),
])
def test_default_destination_preserves_project_research_root(monkeypatch, category, suffix):
    # Inspect the real default without creating anything in tracked outputs.
    directories = []
    monkeypatch.setattr(Path, "mkdir", lambda self, **kwargs: directories.append(self))
    result = reporting.build_report_path(
        category=category, section="example", stem="artifact", suffix=suffix,
    )
    expected = PROJECT / "outputs/research" / category / "example"
    assert result == expected / f"artifact.{suffix}"
    assert directories == [expected]


def test_multiple_plot_helpers_propagate_root_and_preserve_numbers(tmp_path, monkeypatch):
    module = load_script("synthetic/plot_synthetic_reference_data.py")
    monkeypatch.setattr(plt, "show", lambda: None)
    captured = []
    original = module.save_csv

    def record_csv(**kwargs):
        captured.append(kwargs["reports_root"])
        return original(**kwargs)

    monkeypatch.setattr(module, "save_csv", record_csv)
    # Exercise the actual default writer route in an isolated project root.
    default_project = tmp_path / "default-project"
    monkeypatch.setattr(reporting, "find_project_root", lambda path: default_project)
    first, second = default_project / "outputs/research", tmp_path / "explicit"
    try:
        module.main()
        module.main(reports_root=second)
    finally:
        plt.close("all")
    assert captured == [None] * 3 + [second] * 3
    for root in (first, second):
        assert len(list(root.rglob("*.csv"))) == 3
        assert len(list(root.rglob("*.png"))) == 3
        assert len(list(root.rglob("*.svg"))) == 3
        assert all(p.stat().st_size for p in root.rglob("*") if p.is_file())
    for path in first.rglob("*.csv"):
        assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()


@pytest.fixture(scope="module")
def sensitivity_chain(tmp_path_factory):
    """Run a small real producer once, then both real consumers."""
    root = tmp_path_factory.mktemp("sensitivity-reports")
    producer = load_script("sensitivity/report_global_sensitivity.py")
    heatmaps = load_script("sensitivity/plot_global_forward_sensitivity_heatmaps.py")
    locality = load_script("sensitivity/report_forward_sensitivity_locality.py")
    quotes = producer.read_synthetic_ois_quotes_csv(producer.QUOTES_PATH)[:3]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(producer, "read_synthetic_ois_quotes_csv", lambda path: quotes)
        # Real SVGs are sufficient here; PNG and SVG coverage also runs above.
        for module in (producer, heatmaps, locality):
            patch.setattr(module, "save_figure", lambda **kwargs: reporting.save_figure(
                **{**kwargs, "formats": ("svg",)},
            ))
        try:
            producer.main(reports_root=root)
            heatmaps.main(reports_root=root)
            locality.main(reports_root=root)
        finally:
            plt.close("all")
    return root, heatmaps, locality


def test_sensitivity_producer_and_consumers_use_same_root(sensitivity_chain):
    root, heatmaps, locality = sensitivity_chain
    reference_date, scenario, data = heatmaps.read_dense_forward_sensitivity(reports_root=root)
    assert scenario
    assert len(data) == 3
    assert all(len(item["shock_indices"]) == 3 for item in data.values())
    assert len(heatmaps.read_pillar_years(reference_date=reference_date, reports_root=root)) == 3
    loaded_scenario, loaded_date, results = locality.load_locality_results(reports_root=root)
    assert (loaded_scenario, loaded_date) == (scenario, reference_date)
    assert len(results) == 9
    # Reading the checkout's full experiment would produce more than three shocks.
    assert len(list(root.rglob("*.txt"))) == 2
    assert all(p.stat().st_size for p in root.rglob("*") if p.is_file())


def test_sensitivity_metadata_references_existing_outputs_and_selected_inputs(sensitivity_chain):
    root, _, _ = sensitivity_chain
    metadata = root / "metadata/07_global_sensitivity"
    producer = json.loads((metadata / "experiment_metadata.json").read_text())
    heatmaps = json.loads((metadata / "forward_sensitivity_heatmap_metadata.json").read_text())
    locality = json.loads((metadata / "forward_sensitivity_locality_metadata.json").read_text())
    paths = []

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.endswith((".csv", ".svg", ".png", ".txt")):
            paths.append(Path(value))

    for value in (producer["outputs"], heatmaps, locality):
        collect(value)
    assert paths
    for path in paths:
        assert path.is_relative_to(root), path
        assert path.is_file(), path
    for source in (heatmaps, locality):
        serialized = json.dumps(source)
        assert str(root / "tables/07_global_sensitivity/global_forward_sensitivity_dense.csv") in serialized
        assert str(root / "tables/07_global_sensitivity/global_node_sensitivity_long.csv") in serialized


@pytest.mark.parametrize("reader", ["forward", "pillar", "locality"])
def test_missing_explicit_inputs_never_fall_back_to_checkout(tmp_path, reader):
    heatmaps = load_script("sensitivity/plot_global_forward_sensitivity_heatmaps.py")
    locality = load_script("sensitivity/report_forward_sensitivity_locality.py")
    filename = "global_node_sensitivity_long.csv" if reader == "pillar" else "global_forward_sensitivity_dense.csv"
    expected = tmp_path / "tables/07_global_sensitivity" / filename
    with pytest.raises(FileNotFoundError) as exc:
        if reader == "forward":
            heatmaps.read_dense_forward_sensitivity(reports_root=tmp_path)
        elif reader == "pillar":
            heatmaps.read_pillar_years(reference_date=date(2026, 9, 18), reports_root=tmp_path)
        else:
            locality.load_locality_results(reports_root=tmp_path)
    assert str(expected) in str(exc.value)
    assert not list(tmp_path.iterdir())


def test_interpolation_metadata_uses_returned_artifact_paths(tmp_path, monkeypatch):
    module = load_script("interpolation/compare_three_interpolation_methods.py")
    quotes = module.read_synthetic_ois_quotes_csv(module.QUOTES_PATH)[:3]
    monkeypatch.setattr(module, "read_synthetic_ois_quotes_csv", lambda path: quotes)
    # Standard horizon analysis needs >10Y coverage; it is unrelated to routing.
    monkeypatch.setattr(module, "calculate_horizon_recovery_metrics", lambda **kwargs: ())
    # Deliberately use a relative root to exercise unambiguous external references.
    monkeypatch.chdir(tmp_path)
    module.main(reports_root=Path("reports"))
    metadata_path = tmp_path / "reports/metadata/06_interpolation_comparison/experiment_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    for key in ("global_recovery_output", "horizon_recovery_output", "calibration_diagnostics_output"):
        artifact = Path(metadata[key])
        assert artifact.is_absolute()
        assert artifact.is_relative_to(tmp_path / "reports")
        assert artifact.is_file()
    assert metadata["quote_source"] == "data/synthetic/ftiie_ois_quotes_v1.csv"


def test_programmatic_default_propagates_to_every_plot_helper(monkeypatch):
    module = load_script("synthetic/plot_synthetic_reference_data.py")
    roots = []
    for name in ("plot_known_truth_zero_curve", "plot_synthetic_forward_curve", "plot_synthetic_par_curve"):
        monkeypatch.setattr(module, name, lambda *, reports_root: roots.append(reports_root))
    module.main()
    assert roots == [None, None, None]


@pytest.mark.parametrize("relative", [
    "interpolation/compare_three_interpolation_methods.py",
    "sensitivity/report_global_sensitivity.py",
    "sensitivity/plot_global_forward_sensitivity_heatmaps.py",
    "sensitivity/report_forward_sensitivity_locality.py",
])
def test_metadata_preserves_historical_relative_path_presentation(relative):
    module = load_script(relative)
    historical = Path("outputs/research/tables/example.csv")
    assert module.project_relative_path(PROJECT / historical) == historical.as_posix()


def test_locality_missing_node_input_never_falls_back(tmp_path):
    module = load_script("sensitivity/report_forward_sensitivity_locality.py")
    reporting.save_csv(
        reports_root=tmp_path, section="07_global_sensitivity",
        stem="global_forward_sensitivity_dense", header=("reference_date",), rows=(),
    )
    expected = tmp_path / "tables/07_global_sensitivity/global_node_sensitivity_long.csv"
    with pytest.raises(FileNotFoundError) as exc:
        module.load_locality_results(reports_root=tmp_path)
    assert str(expected) in str(exc.value)
