from dataclasses import replace
from datetime import date
import importlib.util
import json
from pathlib import Path

import pytest

from yield_curves import snapshots
from yield_curves.baseline import build_baseline_ftiie_curve, assess_baseline_calibration
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.quote_io import load_ois_quote_dataset_csv, QuoteSource


@pytest.fixture(scope="module")
def run_inputs(tmp_path_factory):
    path = tmp_path_factory.mktemp("inputs") / "quotes.csv"
    path.write_text("tenor,trade_date,contractual_maturity_date,par_rate\n"
                    "1M,2026-09-15,2026-10-18,0.08\n"
                    "3M,2026-09-15,2026-12-18,0.081\n")
    dataset = load_ois_quote_dataset_csv(path, classification=QuoteSource.SYNTHETIC,
                                        source="snapshot integration fixture")
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    result = build_baseline_ftiie_curve(quotes=dataset.quotes, calendar=calendar)
    return dict(result=result, dataset=dataset, calendar=calendar)


def test_publish_accepted_and_preserve_previous_runs(run_inputs, tmp_path):
    first = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    assert first.published
    first_bytes = {p.name: p.read_bytes() for p in first.run_path.iterdir()}
    assert snapshots.resolve_current_snapshot(tmp_path) == first.run_path
    second = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    assert second.run_id != first.run_id
    assert snapshots.resolve_current_snapshot(tmp_path) == second.run_path
    assert {p.name: p.read_bytes() for p in first.run_path.iterdir()} == first_bytes
    meta = json.loads((second.run_path / "metadata.json").read_text())
    assert meta["artifact_schema_version"] == "2.0"
    assert meta["quote_provenance"]["sha256"] == run_inputs["dataset"].provenance.sha256
    assert meta["quote_provenance"]["classification"] == "SYNTHETIC_REFERENCE_DATA"
    cal = json.loads((second.run_path / "calendar.json").read_text())
    assert cal["coverage_start"] == "2026-01-01"
    assert cal["holidays"] == sorted(d.isoformat() for d in run_inputs["calendar"].holidays)


@pytest.mark.parametrize("missing_curve", [False, True])
def test_rejected_run_is_archived_without_replacing_current(run_inputs, tmp_path, missing_curve):
    published = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    calibration = replace(run_inputs["result"].calibration_result, success=False,
                          curve=None if missing_curve else run_inputs["result"].curve)
    acceptance = assess_baseline_calibration(calibration_result=calibration,
                                            quotes=run_inputs["dataset"].quotes,
                                            calendar=run_inputs["calendar"])
    rejected = replace(run_inputs["result"], calibration_result=calibration, acceptance=acceptance)
    archive = snapshots.export_baseline_snapshot(**{**run_inputs, "result": rejected}, output_root=tmp_path)
    assert not archive.published
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    meta = json.loads((archive.run_path / "metadata.json").read_text(),
                      parse_constant=lambda value: pytest.fail(f"Nonstandard JSON: {value}"))
    assert not meta["acceptance"]["accepted_for_use"]
    if missing_curve:
        assert meta["acceptance"]["max_abs_repricing_error_bp"] is None
        assert meta["curve_reference_date"] is None


def test_first_rejected_run_creates_no_current_pointer(run_inputs, tmp_path):
    result = replace(run_inputs["result"], acceptance=replace(
        run_inputs["result"].acceptance, accepted_for_use=False, issues=("TEST_REJECTION",)))
    exported = snapshots.export_baseline_snapshot(**{**run_inputs, "result": result}, output_root=tmp_path)
    assert exported.run_path.is_dir()
    assert not (tmp_path / "current.json").exists()


@pytest.mark.parametrize("failed_file", ["input_quotes.csv", "calendar.json", "curve_nodes.csv",
                                        "quote_repricing.csv", "metadata.json", "manifest.json"])
def test_partial_write_cannot_change_current(run_inputs, tmp_path, monkeypatch, failed_file):
    published = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    original = snapshots._write_csv if failed_file.endswith("csv") else snapshots._write_json
    def interrupted(path, *args):
        if path.name == failed_file:
            path.write_text("partial")
            raise OSError("simulated disk failure")
        return original(path, *args)
    monkeypatch.setattr(snapshots, "_write_csv" if failed_file.endswith("csv") else "_write_json", interrupted)
    with pytest.raises(OSError, match="disk failure"):
        snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert list((tmp_path / "runs").iterdir()) == [published.run_path]


def test_failed_pointer_replace_leaves_complete_unpublished_run(run_inputs, tmp_path, monkeypatch):
    published = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    def interrupted(*args):
        raise OSError("pointer replacement failed")
    monkeypatch.setattr(snapshots.os, "replace", interrupted)
    with pytest.raises(OSError):
        snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert len(list((tmp_path / "runs").iterdir())) == 2
    assert not list(tmp_path.glob(".current-*.tmp"))


def test_resolver_detects_modified_files(run_inputs, tmp_path):
    exported = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    (exported.run_path / "curve_nodes.csv").write_text("corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        snapshots.resolve_current_snapshot(tmp_path)


def test_mismatched_dataset_cannot_be_published(run_inputs, tmp_path):
    dataset = run_inputs["dataset"]
    dataset = replace(dataset, quotes=(replace(dataset.quotes[0], par_rate=0.09), dataset.quotes[1]))
    with pytest.raises(ValueError, match="Dataset does not match"):
        snapshots.export_baseline_snapshot(**{**run_inputs, "dataset": dataset}, output_root=tmp_path)
    assert not (tmp_path / "current.json").exists()


def test_operational_script_uses_exporter_and_preserves_legacy_files(run_inputs, tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("build_snapshot_script", root / "scripts/operational/build_baseline_curve.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    legacy = tmp_path / "curve_nodes.csv"
    legacy.write_text("legacy snapshot")
    result = script.build_snapshot(dataset=run_inputs["dataset"],
                                   calendar=run_inputs["calendar"], output_root=tmp_path)
    assert result.accepted_for_use
    assert legacy.read_text() == "legacy snapshot"
    assert snapshots.resolve_current_snapshot(tmp_path).is_dir()


def test_reader_observes_old_complete_run_until_atomic_commit(run_inputs, tmp_path, monkeypatch):
    first = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    original = snapshots.os.replace
    observed = []
    def observe_commit(source, target):
        observed.append(snapshots.resolve_current_snapshot(tmp_path))
        candidate = json.loads(Path(source).read_text())
        assert (tmp_path / candidate["run_path"] / "manifest.json").is_file()
        original(source, target)
    monkeypatch.setattr(snapshots.os, "replace", observe_commit)
    second = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    assert observed == [first.run_path]
    assert snapshots.resolve_current_snapshot(tmp_path) == second.run_path


def test_metadata_retains_custom_acceptance_tolerances(run_inputs, tmp_path):
    acceptance = assess_baseline_calibration(
        calibration_result=run_inputs["result"].calibration_result,
        quotes=run_inputs["dataset"].quotes, calendar=run_inputs["calendar"],
        pass_tolerance_bp=0.02, fail_tolerance_bp=0.20,
    )
    result = replace(run_inputs["result"], acceptance=acceptance)
    exported = snapshots.export_baseline_snapshot(
        **{**run_inputs, "result": result}, output_root=tmp_path
    )
    metadata = json.loads((exported.run_path / "metadata.json").read_text())
    assert metadata["acceptance"]["pass_tolerance_bp"] == 0.02
    assert metadata["acceptance"]["fail_tolerance_bp"] == 0.20


def _script(relative_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("phase6_script", root / "scripts" / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _input_args(run_inputs, tmp_path):
    calendar = tmp_path / "holidays.csv"
    calendar.write_text("date\n" + "\n".join(
        day.isoformat() for day in sorted(run_inputs["calendar"].holidays)) + "\n")
    return ["--quotes", run_inputs["dataset"].provenance.path,
            "--classification", "SYNTHETIC_REFERENCE_DATA", "--source", "CLI fixture",
            "--calendar", str(calendar), "--calendar-source", "provided fixture",
            "--calendar-start", "2026-01-01", "--calendar-end", "2026-12-31"]


def test_operational_and_assurance_cli_integration(run_inputs, tmp_path, monkeypatch):
    import yield_curves.baseline as baseline
    build = _script("operational/build_baseline_curve.py")
    assurance = _script("assurance/validate_baseline_curve.py")
    args = _input_args(run_inputs, tmp_path)
    output = tmp_path / "published"
    assert build.main(args + ["--output-root", str(output)]) == 0
    run = snapshots.resolve_current_snapshot(output)
    data = json.loads((run / "calendar.json").read_text())
    assert data["provenance"]["kind"] == "PROVIDED"
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    assert assurance.main(["rebuild"] + args) == 0
    def no_solver(**kwargs):
        pytest.fail("Snapshot assurance must not invoke calibration")
    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously", no_solver)
    assert assurance.main(["snapshot", "--output-root", str(output)]) == 0
    assert before == {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}


@pytest.mark.parametrize("missing", ["--quotes", "--classification", "--source", "--calendar",
                                     "--calendar-start", "--calendar-end", "--calendar-source"])
def test_cli_requires_every_input(run_inputs, tmp_path, missing):
    args = _input_args(run_inputs, tmp_path)
    index = args.index(missing)
    del args[index:index + 2]
    with pytest.raises(SystemExit) as error:
        _script("operational/build_baseline_curve.py").main(args + ["--output-root", str(tmp_path)])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        _script("assurance/validate_baseline_curve.py").main(["rebuild"] + args)
    assert error.value.code == 2
    assert not (tmp_path / "current.json").exists()


def test_cli_insufficient_calendar_does_not_publish(run_inputs, tmp_path):
    args = _input_args(run_inputs, tmp_path)
    args[args.index("--calendar-end") + 1] = "2026-10-01"
    with pytest.raises(ValueError):
        _script("operational/build_baseline_curve.py").main(args + ["--output-root", str(tmp_path)])
    assert not (tmp_path / "current.json").exists()


def test_snapshot_assurance_reprices_nodes_even_with_updated_hashes(run_inputs, tmp_path):
    import hashlib
    import csv
    from yield_curves.snapshot_assurance import assess_current_snapshot
    exported = snapshots.export_baseline_snapshot(**run_inputs, output_root=tmp_path)
    nodes = exported.run_path / "curve_nodes.csv"
    with nodes.open() as file:
        reader = csv.DictReader(file)
        header, rows = reader.fieldnames, list(reader)
    rows[0]["discount_factor"] = str(float(rows[0]["discount_factor"]) * 0.99)
    with nodes.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    manifest_path = exported.run_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files_sha256"][nodes.name] = hashlib.sha256(nodes.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    pointer_path = tmp_path / "current.json"
    pointer = json.loads(pointer_path.read_text())
    pointer["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    pointer_path.write_text(json.dumps(pointer))
    assert not assess_current_snapshot(tmp_path).accepted_for_use
    assert _script("assurance/validate_baseline_curve.py").main(
        ["snapshot", "--output-root", str(tmp_path)]) == 1


def test_explicit_demo_uses_synthetic_inputs(tmp_path):
    demo = _script("demo/build_synthetic_baseline.py")
    assert demo.main(["--output-root", str(tmp_path)]) == 0
    run = snapshots.resolve_current_snapshot(tmp_path)
    meta = json.loads((run / "metadata.json").read_text())
    assert meta["quote_provenance"]["classification"] == "SYNTHETIC_REFERENCE_DATA"
    assert meta["quote_count"] == 15
    assert meta["acceptance"]["max_abs_repricing_error_bp"] < 1e-5
    assert json.loads((run / "calendar.json").read_text())["provenance"]["kind"] == "PROJECTED"
