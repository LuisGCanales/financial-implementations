from dataclasses import replace
from datetime import date
import importlib.util
import json
from pathlib import Path

import pytest

from yield_curves import snapshots, execution as workflow
from yield_curves.execution import build_baseline_execution
from yield_curves.baseline import assess_baseline_calibration
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
    execution = build_baseline_execution(dataset=dataset, calendar=calendar)
    return dict(execution=execution, result=execution.result, dataset=dataset, calendar=calendar)


def test_publish_accepted_and_preserve_previous_runs(run_inputs, tmp_path):
    first = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert first.published
    first_bytes = {p.name: p.read_bytes() for p in first.run_path.iterdir()}
    assert snapshots.resolve_current_snapshot(tmp_path) == first.run_path
    second = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert second.run_id != first.run_id
    assert snapshots.resolve_current_snapshot(tmp_path) == second.run_path
    assert {p.name: p.read_bytes() for p in first.run_path.iterdir()} == first_bytes
    meta = json.loads((second.run_path / "metadata.json").read_text())
    assert meta["artifact_schema_version"] == "3.0"
    assert run_inputs["result"].acceptance.is_standard_acceptance
    assert "acceptance_policy" in meta["acceptance"]
    assert "acceptance_policy" in meta["acceptance"]["binding"]
    assert "acceptance_policy" in meta["acceptance"]["binding"]["financial_context"]["policy"]
    assert meta["quote_provenance"]["sha256"] == run_inputs["dataset"].provenance.sha256
    assert meta["quote_provenance"]["classification"] == "SYNTHETIC_REFERENCE_DATA"
    cal = json.loads((second.run_path / "calendar.json").read_text())
    assert cal["coverage_start"] == "2026-01-01"
    assert cal["holidays"] == sorted(d.isoformat() for d in run_inputs["calendar"].holidays)


@pytest.mark.parametrize("missing_curve", [False, True])
def test_rejected_run_is_archived_without_replacing_current(run_inputs, tmp_path, monkeypatch, missing_curve):
    published = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    rejected = _rejected_execution(run_inputs, monkeypatch, missing_curve)
    archive = snapshots.export_baseline_snapshot(execution=rejected, output_root=tmp_path)
    assert not archive.published
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    meta = json.loads((archive.run_path / "metadata.json").read_text(),
                      parse_constant=lambda value: pytest.fail(f"Nonstandard JSON: {value}"))
    assert meta["status"] == "rejected"
    assert not meta["acceptance"]["accepted_for_use"]
    if missing_curve:
        assert meta["acceptance"]["max_abs_repricing_error_bp"] is None
        assert meta["curve_reference_date"] is None


def _rejected_execution(run_inputs, monkeypatch, missing_curve=False):
    import yield_curves.baseline as baseline
    calibration = replace(run_inputs["result"].calibration_result, success=False,
                          curve=None if missing_curve else run_inputs["result"].curve)
    monkeypatch.setattr(baseline, "calibrate_ftiie_ois_curve_simultaneously", lambda **kw: calibration)
    return build_baseline_execution(dataset=run_inputs["dataset"], calendar=run_inputs["calendar"])


def test_first_rejected_run_creates_no_current_pointer(run_inputs, tmp_path, monkeypatch):
    execution = _rejected_execution(run_inputs, monkeypatch)
    exported = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    assert exported.run_path.is_dir()
    assert not (tmp_path / "current.json").exists()


@pytest.mark.parametrize("failed_file", ["input_quotes.csv", "calendar.json", "curve_nodes.csv",
                                        "quote_repricing.csv", "metadata.json", "manifest.json"])
def test_partial_write_cannot_change_current(run_inputs, tmp_path, monkeypatch, failed_file):
    published = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    original = snapshots._write_csv if failed_file.endswith("csv") else snapshots._write_json
    def interrupted(path, *args):
        if path.name == failed_file:
            path.write_text("partial")
            raise OSError("simulated disk failure")
        return original(path, *args)
    monkeypatch.setattr(snapshots, "_write_csv" if failed_file.endswith("csv") else "_write_json", interrupted)
    with pytest.raises(OSError, match="disk failure"):
        snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert list((tmp_path / "runs").iterdir()) == [published.run_path]


def test_failed_pointer_replace_leaves_complete_unpublished_run(run_inputs, tmp_path, monkeypatch):
    published = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    def interrupted(*args):
        raise OSError("pointer replacement failed")
    monkeypatch.setattr(snapshots.os, "replace", interrupted)
    with pytest.raises(OSError):
        snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert len(list((tmp_path / "runs").iterdir())) == 2
    assert not list(tmp_path.glob(".current-*.tmp"))


def test_resolver_detects_modified_files(run_inputs, tmp_path):
    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    (exported.run_path / "curve_nodes.csv").write_text("corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        snapshots.resolve_current_snapshot(tmp_path)


def test_separate_result_and_provenance_cannot_be_published(run_inputs, tmp_path):
    with pytest.raises(TypeError):
        snapshots.export_baseline_snapshot(result=run_inputs["result"],
            dataset=run_inputs["dataset"], calendar=run_inputs["calendar"], output_root=tmp_path)
    with pytest.raises(TypeError, match="issued by"):
        workflow.ExecutionEnvelope(result=run_inputs["result"])
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
    first = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    original = snapshots.os.replace
    observed = []
    def observe_commit(source, target):
        observed.append(snapshots.resolve_current_snapshot(tmp_path))
        candidate = json.loads(Path(source).read_text())
        assert (tmp_path / candidate["run_path"] / "manifest.json").is_file()
        original(source, target)
    monkeypatch.setattr(snapshots.os, "replace", observe_commit)
    second = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert observed == [first.run_path]
    assert snapshots.resolve_current_snapshot(tmp_path) == second.run_path


def test_custom_pass_cannot_publish(run_inputs, tmp_path):
    import copy
    snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    pointer = (tmp_path / "current.json").read_bytes()
    acceptance = assess_baseline_calibration(
        calibration_result=run_inputs["result"].calibration_result,
        quotes=run_inputs["dataset"].quotes, calendar=run_inputs["calendar"],
        pass_tolerance_bp=0.02, fail_tolerance_bp=0.20,
    )
    assert acceptance.accepted_for_use and not acceptance.is_standard_acceptance
    result = replace(run_inputs["result"], acceptance=acceptance, financial_context=None)
    execution = copy.copy(run_inputs["execution"])
    object.__setattr__(execution, "result", result)
    with pytest.raises(ValueError, match="custom"):
        snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert len(list((tmp_path / "runs").iterdir())) == 1


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
    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
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
    with pytest.raises(ValueError, match="binding mismatch"):
        assess_current_snapshot(tmp_path)


def test_explicit_demo_uses_synthetic_inputs(tmp_path):
    demo = _script("demo/build_synthetic_baseline.py")
    assert demo.main(["--output-root", str(tmp_path)]) == 0
    run = snapshots.resolve_current_snapshot(tmp_path)
    meta = json.loads((run / "metadata.json").read_text())
    assert meta["quote_provenance"]["classification"] == "SYNTHETIC_REFERENCE_DATA"
    assert meta["quote_count"] == 15
    assert meta["acceptance"]["max_abs_repricing_error_bp"] < 1e-5
    assert json.loads((run / "calendar.json").read_text())["provenance"]["kind"] == "PROJECTED"


@pytest.mark.parametrize("changed", ["trade_date", "contractual_maturity_date", "par_rate",
    "holidays", "weekend_days", "coverage_start", "coverage_end", "context", "policy",
    "curve", "acceptance", "quote_provenance", "calendar_provenance"])
def test_execution_mixing_rejected_before_writes(run_inputs, tmp_path, changed):
    import copy
    from datetime import timedelta
    execution = copy.deepcopy(run_inputs["execution"])
    inputs = execution.inputs
    if changed in {"trade_date", "contractual_maturity_date", "par_rate"}:
        quote = inputs.quotes[0]
        value = 0.09 if changed == "par_rate" else getattr(quote, changed) + timedelta(days=1)
        altered = replace(inputs, quotes=(replace(quote, **{changed: value}), inputs.quotes[1]))
        object.__setattr__(execution, "inputs", altered)
    elif changed in {"holidays", "weekend_days", "coverage_start", "coverage_end"}:
        calendar = inputs.calendar
        if changed == "holidays":
            value = tuple(sorted((*calendar.holidays, date(2026, 10, 1))))
        elif changed == "weekend_days":
            value = (4, 5, 6)
        else:
            value = getattr(calendar, changed) + timedelta(days=1)
        object.__setattr__(execution, "inputs", replace(inputs, calendar=replace(calendar, **{changed: value})))
    elif changed == "context":
        object.__setattr__(execution.result, "financial_context", replace(
            execution.result.financial_context, inputs=replace(inputs, reference_date=date(2026, 9, 21))))
    elif changed == "policy":
        context = execution.result.financial_context
        object.__setattr__(execution.result, "financial_context", replace(context,
            policy=replace(context.policy, baseline_identifier="OTHER_POLICY")))
    elif changed == "curve":
        curve = execution.result.curve
        object.__setattr__(curve, "discount_factors", tuple(df * 0.99 for df in curve.discount_factors))
    elif changed == "acceptance":
        # A real acceptance for another evaluated payload, not just a label edit.
        other = replace(execution.result.calibration_result, success=False)
        acceptance = assess_baseline_calibration(calibration_result=other,
            quotes=inputs.quotes, calendar=inputs.calendar.to_calendar())
        object.__setattr__(execution.result, "acceptance", acceptance)
    else:
        provenance = getattr(execution, changed)
        object.__setattr__(execution, changed, replace(provenance, source="unrelated source"))
    with pytest.raises(ValueError, match="mismatch|Unsupported"):
        snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_provenance_and_inputs_are_captured_before_build(run_inputs, tmp_path, monkeypatch):
    from yield_curves.calendar_io import build_mxmc_calendar_from_csv
    quotes_path = tmp_path / "source.csv"
    quotes_path.write_bytes(Path(run_inputs["dataset"].provenance.path).read_bytes())
    calendar_path = tmp_path / "holidays.csv"
    calendar_path.write_text("date\n2026-09-16\n")
    dataset = load_ois_quote_dataset_csv(quotes_path, classification=QuoteSource.UNKNOWN, source="provided quotes")
    calendar = build_mxmc_calendar_from_csv(calendar_path, coverage_start=date(2026, 1, 1),
        coverage_end=date(2026, 12, 31), source="provided holidays")
    original = workflow.build_baseline_ftiie_curve
    observed = []
    def build(**kwargs):
        observed.append(kwargs)
        quotes_path.write_text("source changed during build")
        calendar_path.unlink()
        object.__setattr__(dataset, "provenance", replace(dataset.provenance, source="late declaration"))
        return original(**kwargs)
    provenance = dataset.provenance
    monkeypatch.setattr(workflow, "build_baseline_ftiie_curve", build)
    execution = build_baseline_execution(dataset=dataset, calendar=calendar)
    assert execution.quote_provenance == provenance
    assert execution.calendar_provenance == calendar.provenance
    assert observed[0]["quotes"] == execution.inputs.quotes
    assert observed[0]["calendar"].provenance is None
    exported = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path / "output")
    metadata = json.loads((exported.run_path / "metadata.json").read_text())
    assert metadata["quote_provenance"]["source"] == "provided quotes"
    assert metadata["quote_provenance"]["sha256"] == provenance.sha256
    assert metadata["execution"]["calendar_provenance"]["sha256"] == calendar.provenance.sha256


def _rehash(run, root):
    """Repair outer checksums to test semantic checks rather than file hashing."""
    import hashlib
    path = run / "manifest.json"
    manifest = json.loads(path.read_text())
    for name in manifest["files_sha256"]:
        manifest["files_sha256"][name] = hashlib.sha256((run / name).read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest))
    pointer_path = root / "current.json"
    pointer = json.loads(pointer_path.read_text())
    pointer["manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    pointer_path.write_text(json.dumps(pointer))


@pytest.mark.parametrize("target", ["pointer_schema", "manifest_schema", "metadata_schema",
    "policy", "acceptance_policy", "node_date", "quote_date", "quote_rate", "calendar_holidays",
    "calendar_weekends", "calendar_coverage", "quote_provenance", "calendar_provenance",
    "acceptance_check", "solver", "run_identity", "execution_identity"])
def test_assurance_rejects_incoherence_with_rehashed_files(run_inputs, tmp_path, target):
    import csv
    from yield_curves.snapshot_assurance import assess_current_snapshot
    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    run = exported.run_path
    if target in {"node_date", "quote_date", "quote_rate"}:
        path = run / ("curve_nodes.csv" if target == "node_date" else "input_quotes.csv")
        with path.open() as file:
            reader = csv.DictReader(file)
            header, rows = reader.fieldnames, list(reader)
        field, value = {"node_date": ("pillar_date", "2026-10-23"),
                        "quote_date": ("trade_date", "2026-09-14"),
                        "quote_rate": ("par_rate", "0.09")}[target]
        rows[0][field] = value
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
    else:
        path = (tmp_path / "current.json" if target == "pointer_schema" else
                run / "manifest.json" if target == "manifest_schema" else
                run / "calendar.json" if target.startswith("calendar_") else run / "metadata.json")
        data = json.loads(path.read_text())
        if target.endswith("schema"):
            data["artifact_schema_version"] = "2.0"
        elif target == "policy":
            data["execution"]["financial_context"]["policy"]["baseline_identifier"] = "UNSUPPORTED"
        elif target == "acceptance_policy":
            data["acceptance"]["acceptance_policy"]["kind"] = "CUSTOM_ANALYTICAL_ASSESSMENT"
        elif target == "calendar_holidays":
            data["holidays"].append("2026-10-01")
        elif target == "calendar_weekends":
            data["weekend_days"] = [4, 5, 6]
        elif target == "calendar_coverage":
            data["coverage_end"] = "2027-01-01"
        elif target == "calendar_provenance":
            data["provenance"]["source"] = "other source"
        elif target == "quote_provenance":
            data["quote_provenance"]["sha256"] = "0" * 64
        elif target == "acceptance_check":
            data["acceptance"]["checks"][0]["market_quote"] = 0.09
        elif target == "solver":
            data["solver"]["success"] = False
        elif target == "execution_identity":
            data["execution"]["execution_id"] = "0" * 32
        else:
            data["run_id"] = "0" * 32
        path.write_text(json.dumps(data))
    _rehash(run, tmp_path)
    with pytest.raises(ValueError):
        assess_current_snapshot(tmp_path)


def test_assurance_unsupported_policy_is_explicit(run_inputs, tmp_path):
    from yield_curves.snapshot_assurance import assess_current_snapshot
    run = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path).run_path
    path = run / "metadata.json"
    data = json.loads(path.read_text())
    data["execution"]["financial_context"]["policy"]["baseline_identifier"] = "FUTURE_V2"
    digest = workflow.fingerprint(data["execution"])
    data["execution_binding_sha256"] = digest
    path.write_text(json.dumps(data))
    for path in (run / "manifest.json", tmp_path / "current.json"):
        data = json.loads(path.read_text())
        data["execution_binding_sha256"] = digest
        path.write_text(json.dumps(data))
    _rehash(run, tmp_path)
    with pytest.raises(ValueError, match="Unsupported baseline policy"):
        assess_current_snapshot(tmp_path)


@pytest.mark.parametrize("phase", ["staging_sync", "rename", "runs_sync", "pointer_write", "after_replace", "root_sync"])
def test_commit_failure_semantics(run_inputs, tmp_path, monkeypatch, phase):
    first = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    previous = (tmp_path / "current.json").read_bytes()
    sync, rename, write, replace_pointer = snapshots._sync_directory, Path.rename, snapshots._write_json, snapshots.os.replace
    def failing_sync(path):
        if ((phase == "staging_sync" and path.name.startswith(".staging-"))
                or (phase == "runs_sync" and path.name == "runs")
                or (phase == "root_sync" and path == tmp_path)):
            raise OSError("injected failure")
        sync(path)
    def failing_rename(path, target):
        if phase == "rename":
            raise OSError("injected failure")
        return rename(path, target)
    def failing_write(path, data):
        if phase == "pointer_write" and path.name.startswith(".current-"):
            raise OSError("injected failure")
        write(path, data)
    def failing_replace(source, target):
        replace_pointer(source, target)
        if phase == "after_replace":
            raise OSError("injected failure")
    monkeypatch.setattr(snapshots, "_sync_directory", failing_sync)
    monkeypatch.setattr(Path, "rename", failing_rename)
    monkeypatch.setattr(snapshots, "_write_json", failing_write)
    monkeypatch.setattr(snapshots.os, "replace", failing_replace)
    with pytest.raises(OSError, match="injected failure"):
        snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    after_commit = phase in {"after_replace", "root_sync"}
    assert ((tmp_path / "current.json").read_bytes() != previous) == after_commit
    current = snapshots.resolve_current_snapshot(tmp_path)
    assert (current != first.run_path) == after_commit
    assert len(list((tmp_path / "runs").iterdir())) == (1 if phase in {"staging_sync", "rename"} else 2)
    assert not list(tmp_path.glob(".current-*.tmp"))


def test_assurance_reprices_without_solver_or_any_write(run_inputs, tmp_path, monkeypatch):
    import builtins
    import io
    import yield_curves.baseline as baseline
    import yield_curves.calibration as calibration
    import yield_curves.snapshot_assurance as assurance
    snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("Assurance attempted solver or write")
    for module, name in ((baseline, "calibrate_ftiie_ois_curve_simultaneously"),
                         (calibration, "calibrate_ftiie_ois_curve_simultaneously"),
                         (snapshots, "export_baseline_snapshot")):
        monkeypatch.setattr(module, name, forbidden)
    for module in (builtins, io):
        original = module.open
        def readonly(file, mode="r", *args, _open=original, **kwargs):
            assert not any(c in mode for c in "wax+")
            return _open(file, mode, *args, **kwargs)
        monkeypatch.setattr(module, "open", readonly)
    count = []
    original = baseline._independently_reprice
    def reprice(**kwargs):
        count.append(True)
        return original(**kwargs)
    monkeypatch.setattr(baseline, "_independently_reprice", reprice)
    assert assurance.assess_current_snapshot(tmp_path).accepted_for_use
    assert count == [True]


@pytest.mark.parametrize("version", ["1.0", "2.0", "999.0"])
def test_legacy_and_unknown_schemas_are_not_promoted_or_migrated(run_inputs, tmp_path, version):
    from yield_curves.snapshot_assurance import assess_current_snapshot
    snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    path = tmp_path / "current.json"
    data = json.loads(path.read_text())
    data["artifact_schema_version"] = version
    path.write_text(json.dumps(data))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="Unsupported snapshot schema"):
        assess_current_snapshot(tmp_path)
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_flat_legacy_is_never_current(tmp_path):
    (tmp_path / "metadata.json").write_text('{"artifact_schema_version": "1.0"}')
    with pytest.raises(FileNotFoundError):
        snapshots.resolve_current_snapshot(tmp_path)


@pytest.mark.parametrize("reader_name", ["resolver", "assurance"])
@pytest.mark.parametrize("legacy_directory", [".", "legacy/schema-1.0"])
def test_legacy_artifacts_are_not_a_current_source(tmp_path, reader_name, legacy_directory):
    from yield_curves.snapshot_assurance import assess_current_snapshot

    archive = tmp_path / legacy_directory
    archive.mkdir(parents=True, exist_ok=True)
    historical = {
        "metadata.json": b'{"artifact_schema_version": "1.0", "accepted_for_use": true}\n',
        "curve_nodes.csv": b"historical curve\n",
        "quote_repricing.csv": b"historical repricing\n",
    }
    for name, content in historical.items():
        (archive / name).write_bytes(content)
    reader = snapshots.resolve_current_snapshot if reader_name == "resolver" else assess_current_snapshot
    with pytest.raises(FileNotFoundError, match="current.json"):
        reader(tmp_path)
    assert {p.name: p.read_bytes() for p in archive.iterdir()} == historical
    assert not (tmp_path / "runs").exists()
