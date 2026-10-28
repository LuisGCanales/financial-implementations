from dataclasses import replace
from datetime import date
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from yield_curves import snapshots, execution as workflow
from yield_curves.execution import build_baseline_execution
from yield_curves.baseline import STANDARD_ACCEPTANCE_POLICY, assess_baseline_calibration
from yield_curves.calendars import BusinessCalendar, CalendarProvenance, CalendarSource
from yield_curves.research.calendars import (build_projected_mxmc_calendar)
from yield_curves.quote_io import (
    load_ois_quote_dataset_csv, OISQuoteDataset, QuoteProvenance, QuoteSource,
)
from yield_curves.quotes import OISQuote


def _assert_complete_run_archive(run_path, *, execution, accepted):
    """Inspect archive bytes directly, including runs that are never current."""
    csv_headers = {
        "input_quotes.csv": ["tenor", "trade_date", "contractual_maturity_date", "par_rate"],
        "curve_nodes.csv": ["tenor", "pillar_date", "discount_factor", "continuous_zero_rate"],
        "quote_repricing.csv": ["tenor", "input_quote", "repriced_quote", "error_bp", "status"],
    }
    payloads = set(csv_headers) | {"calendar.json", "metadata.json"}
    assert {path.name for path in run_path.iterdir()} == payloads | {"manifest.json"}
    assert all(path.is_file() for path in run_path.iterdir())
    records = {}
    for name in ("calendar.json", "metadata.json", "manifest.json"):
        records[name] = json.loads(
            (run_path / name).read_text(encoding="utf-8"),
            parse_constant=lambda value: pytest.fail(f"Nonstandard JSON: {value}"),
        )
        assert isinstance(records[name], dict)
    for name, header in csv_headers.items():
        with (run_path / name).open(encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file, strict=True))
        assert rows and rows[0] == header
        assert all(len(row) == len(header) for row in rows[1:])
    metadata, manifest = records["metadata.json"], records["manifest.json"]
    assert set(manifest["files_sha256"]) == payloads
    for name in payloads:
        assert hashlib.sha256((run_path / name).read_bytes()).hexdigest() == manifest["files_sha256"][name]
    assert metadata["artifact_schema_version"] == manifest["artifact_schema_version"] == "3.0"
    assert metadata["run_id"] == manifest["run_id"] == run_path.name
    assert metadata["created_at_utc"] == manifest["created_at_utc"]
    assert metadata["status"] == ("accepted" if accepted else "rejected")
    assert metadata["acceptance"]["accepted_for_use"] is accepted
    assert manifest["accepted_for_use"] is accepted
    assert metadata["execution_binding_sha256"] == manifest["execution_binding_sha256"] == execution.binding_sha256
    assert metadata["execution"] == execution.record()
    return metadata


def _block_snapshot_writes(blocked):
    """Install only inside a monkeypatch context, after legitimate setup."""
    targets = [
        (Path, "mkdir"), (snapshots.tempfile, "mkdtemp"),
        (snapshots, "_write_csv"), (snapshots, "_write_json"),
        (Path, "rename"), (snapshots.os, "replace"),
    ]
    functions = [getattr(owner, name) for owner, name in targets]
    # Also cover any definition-time aliases imported directly by the exporter.
    targets.extend((snapshots, name) for name, value in tuple(vars(snapshots).items())
                   if any(value is function for function in functions)
                   and (snapshots, name) not in targets)
    calls = []

    def sentinel(location):
        def forbidden(*args, **kwargs):
            calls.append(location)
            pytest.fail(f"Publication guard attempted a write: {location}")
        return forbidden

    for owner, name in targets:
        blocked.setattr(owner, name, sentinel(f"{owner.__name__}.{name}"))
    return calls


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


def test_same_financial_inputs_keep_distinct_declared_provenance():
    quotes = (
        OISQuote("1M", date(2026, 9, 15), date(2026, 10, 18), 0.08),
        OISQuote("3M", date(2026, 9, 15), date(2026, 12, 18), 0.081),
    )
    # These in-memory declarations are retained, not authenticated as market data.
    provenance_a = QuoteProvenance(QuoteSource.UNKNOWN, "caller A", "/declared/a.csv", "a" * 64)
    provenance_b = QuoteProvenance(QuoteSource.OBSERVED, "caller B", "/declared/b.csv", "b" * 64)
    dataset_a = OISQuoteDataset(quotes, provenance_a)
    dataset_b = OISQuoteDataset(quotes, provenance_b)
    calendar_provenance_a = CalendarProvenance("calendar A", CalendarSource.PROJECTED, "c" * 64)
    calendar_provenance_b = CalendarProvenance("calendar B", CalendarSource.PROVIDED, "d" * 64)
    calendar_a = BusinessCalendar(
        "SAME", holidays=frozenset({date(2026, 9, 16)}), weekend_days=frozenset({5, 6}),
        coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31),
        provenance=calendar_provenance_a,
    )
    calendar_b = replace(calendar_a, provenance=calendar_provenance_b)
    execution_a = build_baseline_execution(dataset=dataset_a, calendar=calendar_a)
    execution_b = build_baseline_execution(dataset=dataset_b, calendar=calendar_b)
    assert execution_a.inputs == execution_b.inputs
    assert execution_a.inputs.quotes == quotes
    assert execution_a.result.financial_context == execution_b.result.financial_context
    assert execution_a.result.financial_context.policy == execution_b.result.financial_context.policy
    assert execution_a.result.acceptance.acceptance_policy == execution_b.result.acceptance.acceptance_policy
    for execution, provenance, calendar_provenance in (
        (execution_a, provenance_a, calendar_provenance_a),
        (execution_b, provenance_b, calendar_provenance_b),
    ):
        assert execution.result.acceptance.is_standard_acceptance
        assert execution.result.accepted_for_use
        checks = execution.result.acceptance.checks
        assert [(check.tenor, check.market_quote) for check in checks] == [
            (quote.tenor, quote.par_rate) for quote in quotes
        ]
        assert all(check.status.value == "PASS" for check in checks)
        assert [check.model_quote for check in checks] == pytest.approx(
            [quote.par_rate for quote in quotes], abs=1e-6, rel=0,
        )
        assert execution.quote_provenance == provenance
        assert execution.calendar_provenance == calendar_provenance
        record = execution.record()
        assert record["quote_provenance"] == {
            "classification": provenance.classification.value, "source": provenance.source,
            "path": provenance.path, "sha256": provenance.sha256,
        }
        assert record["calendar_provenance"] == {
            "source": calendar_provenance.source, "kind": calendar_provenance.kind.value,
            "sha256": calendar_provenance.sha256,
        }
        financial_context = json.dumps(record["financial_context"], sort_keys=True)
        for key in ("source", "path", "sha256", "classification", "provenance",
                    "quote_provenance", "calendar_provenance"):
            assert f'"{key}":' not in financial_context
        for declaration in (provenance.source, provenance.path, provenance.sha256,
                            calendar_provenance.source, calendar_provenance.sha256):
            assert declaration not in financial_context
        assert workflow.fingerprint(record) == execution.binding_sha256
    # Execution UUID/time also contribute: unequal hashes alone cannot isolate provenance.
    assert execution_a.binding_sha256 != execution_b.binding_sha256


def test_h01_padded_in_memory_execution_round_trips_with_raw_csv_provenance(tmp_path):
    from yield_curves.snapshot_assurance import assess_current_snapshot

    header = "tenor,trade_date,contractual_maturity_date,par_rate\n"
    rows = ("1M,2026-09-15,2026-10-18,0.08\n"
            "3M,2026-09-15,2026-12-18,0.081\n")
    canonical_path, padded_path = tmp_path / "canonical.csv", tmp_path / "padded.csv"
    canonical_path.write_text(header + rows, encoding="utf-8")
    padded_path.write_text(header + rows.replace("1M,", " 1M ,").replace("3M,", "3M ,"),
                           encoding="utf-8")
    datasets = tuple(load_ois_quote_dataset_csv(
        path, classification=QuoteSource.UNKNOWN, source=f" source {path.stem} ",
    ) for path in (canonical_path, padded_path))
    assert datasets[0].quotes == datasets[1].quotes  # Real CSV adapter convergence.
    assert datasets[0].provenance.sha256 != datasets[1].provenance.sha256
    # Feed raw labels through the in-memory boundary as well as the CSV reader.
    padded_quotes = tuple(replace(q, tenor=tenor) for q, tenor in zip(
        datasets[1].quotes, (" 1M ", "3M "), strict=True,
    ))
    padded_dataset = replace(datasets[1], quotes=padded_quotes)
    calendar = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
    executions = tuple(build_baseline_execution(dataset=dataset, calendar=calendar)
                       for dataset in (datasets[0], padded_dataset))
    assert executions[0].inputs == executions[1].inputs
    assert executions[0].result.financial_context == executions[1].result.financial_context
    for execution, dataset, path in zip(executions, datasets, (canonical_path, padded_path), strict=True):
        assert execution.inputs.quotes == datasets[0].quotes
        assert execution.result.financial_context.inputs == execution.inputs
        assert execution.result.accepted_for_use is True
        assert execution.result.acceptance.acceptance_policy == STANDARD_ACCEPTANCE_POLICY
        assert execution.result.acceptance.is_standard_acceptance
        assert tuple(c.tenor for c in execution.result.acceptance.checks) == ("1M", "3M")
        provenance = dataset.provenance
        assert provenance.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
        assert provenance.path == str(path.resolve())
        assert provenance.source == f" source {path.stem} "
        assert provenance.classification is QuoteSource.UNKNOWN
        assert execution.quote_provenance == provenance
        assert execution.calendar_provenance == calendar.provenance
        record = execution.record()
        root = tmp_path / path.stem
        exported = snapshots.export_baseline_snapshot(execution=execution, output_root=root)
        assert exported.published is True
        metadata = _assert_complete_run_archive(exported.run_path, execution=execution, accepted=True)
        assert metadata["quote_provenance"] == record["quote_provenance"]
        with (exported.run_path / "input_quotes.csv").open(newline="", encoding="utf-8") as file:
            archived_quotes = list(csv.DictReader(file))
        assert archived_quotes == [
            {"tenor": q.tenor, "trade_date": q.trade_date.isoformat(),
             "contractual_maturity_date": q.contractual_maturity_date.isoformat(),
             "par_rate": str(q.par_rate)} for q in datasets[0].quotes
        ]
        before_read = _snapshot_tree_state(tmp_path)
        assert snapshots.resolve_current_snapshot(root) == exported.run_path
        assert _snapshot_tree_state(tmp_path) == before_read
        assessment = assess_current_snapshot(root)
        assert assessment.accepted_for_use is True
        assert assessment.is_standard_acceptance
        assert assessment.acceptance_policy == STANDARD_ACCEPTANCE_POLICY
        assert assessment.binding.evaluation_inputs == execution.inputs
        assert assessment.checks == execution.result.acceptance.checks
        assert _snapshot_tree_state(tmp_path) == before_read
        assert execution.record() == record
        execution.validate()
    assert padded_dataset.provenance == datasets[1].provenance
    assert tuple(q.tenor for q in padded_dataset.quotes) == (" 1M ", "3M ")
    # Separate runs carry UUID/time; financial equivalence does not imply equal bindings.


def test_export_uses_completed_execution_without_solver(run_inputs, tmp_path, monkeypatch):
    import scipy.optimize as optimize
    from yield_curves import baseline, bootstrap, calibration

    # The fixture completes construction before any solver entrypoint is blocked.
    execution = run_inputs["execution"]
    assert execution.result.acceptance.is_standard_acceptance
    assert execution.result.accepted_for_use
    execution.validate()
    forbidden_functions = (
        workflow.build_baseline_execution,
        baseline.build_baseline_ftiie_curve,
        bootstrap.bootstrap_ftiie_ois_curve,
        bootstrap.bootstrap_ftiie_ois_curve_with_method,
        calibration.calibrate_ftiie_ois_curve_simultaneously,
        optimize.brentq,
        optimize.least_squares,
    )
    calls = []

    def sentinel(location):
        def forbidden(*args, **kwargs):
            calls.append(location)
            pytest.fail(f"Exporter invoked forbidden construction/solver: {location}")
        return forbidden

    with monkeypatch.context() as blocked:
        # Match original function identities, including already imported aliases
        # (and any alias added to snapshots), not only definition-site names.
        for module in (snapshots, workflow, baseline, bootstrap, calibration, optimize):
            for name, value in tuple(vars(module).items()):
                if any(value is function for function in forbidden_functions):
                    blocked.setattr(module, name, sentinel(f"{module.__name__}.{name}"))
        exported = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)

    assert calls == []
    assert exported.published is True
    assert exported.run_path == tmp_path / "runs" / exported.run_id
    assert exported.run_path.is_dir()
    assert {path.name for path in exported.run_path.iterdir()} == {
        "input_quotes.csv", "calendar.json", "curve_nodes.csv",
        "quote_repricing.csv", "metadata.json", "manifest.json",
    }
    assert all(path.is_file() and path.stat().st_size > 0
               for path in exported.run_path.iterdir())
    pointer = json.loads((tmp_path / "current.json").read_text())
    assert pointer["run_id"] == exported.run_id
    assert pointer["run_path"] == f"runs/{exported.run_id}"
    assert snapshots.resolve_current_snapshot(tmp_path) == exported.run_path
    metadata = json.loads((exported.run_path / "metadata.json").read_text())
    assert metadata["execution"] == execution.record()
    assert metadata["execution_binding_sha256"] == execution.binding_sha256


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
    previous_bytes = {path.name: path.read_bytes() for path in published.run_path.iterdir()}
    rejected = _rejected_execution(run_inputs, monkeypatch, missing_curve)
    archive = snapshots.export_baseline_snapshot(execution=rejected, output_root=tmp_path)
    assert not archive.published
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert {path.name: path.read_bytes() for path in published.run_path.iterdir()} == previous_bytes
    meta = _assert_complete_run_archive(archive.run_path, execution=rejected, accepted=False)
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
    previous_bytes = {path.name: path.read_bytes() for path in published.run_path.iterdir()}
    previous_runs = set((tmp_path / "runs").iterdir())
    def interrupted(*args):
        raise OSError("pointer replacement failed")
    monkeypatch.setattr(snapshots.os, "replace", interrupted)
    with pytest.raises(OSError):
        snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert (tmp_path / "current.json").read_bytes() == pointer
    assert snapshots.resolve_current_snapshot(tmp_path) == published.run_path
    assert len(list((tmp_path / "runs").iterdir())) == 2
    assert not list(tmp_path.glob(".current-*.tmp"))
    assert {path.name: path.read_bytes() for path in published.run_path.iterdir()} == previous_bytes
    new_runs = set((tmp_path / "runs").iterdir()) - previous_runs
    assert len(new_runs) == 1
    _assert_complete_run_archive(new_runs.pop(), execution=run_inputs["execution"], accepted=True)


def test_resolver_detects_modified_files(run_inputs, tmp_path):
    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    (exported.run_path / "curve_nodes.csv").write_text("corrupted")
    with pytest.raises(ValueError, match="checksum mismatch"):
        snapshots.resolve_current_snapshot(tmp_path)


def test_separate_result_and_provenance_cannot_be_published(run_inputs, tmp_path, monkeypatch):
    with pytest.raises(TypeError):
        snapshots.export_baseline_snapshot(result=run_inputs["result"],
            dataset=run_inputs["dataset"], calendar=run_inputs["calendar"], output_root=tmp_path)
    with pytest.raises(TypeError, match="issued by"):
        workflow.ExecutionEnvelope(result=run_inputs["result"])
    assert not (tmp_path / "current.json").exists()
    root = tmp_path / "absent"
    assert not root.exists()
    with monkeypatch.context() as blocked:
        calls = _block_snapshot_writes(blocked)
        with pytest.raises(TypeError, match="ExecutionEnvelope"):
            snapshots.export_baseline_snapshot(execution=run_inputs["result"], output_root=root)
    assert calls == []
    assert not root.exists()
    assert not (root / "runs").exists()
    assert not (root / "current.json").exists()


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


@pytest.mark.parametrize("existing_root", [True, False])
def test_custom_pass_cannot_publish(run_inputs, tmp_path, monkeypatch, existing_root):
    import copy
    root = tmp_path / "output"
    if existing_root:
        snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=root)
        pointer = (root / "current.json").read_bytes()
    else:
        assert not root.exists()
    inventory = {path.relative_to(root) for path in root.rglob("*")}
    previous_bytes = {path.relative_to(root): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
    acceptance = assess_baseline_calibration(
        calibration_result=run_inputs["result"].calibration_result,
        quotes=run_inputs["dataset"].quotes, calendar=run_inputs["calendar"],
        pass_tolerance_bp=0.02, fail_tolerance_bp=0.20,
    )
    assert acceptance.accepted_for_use and not acceptance.is_standard_acceptance
    result = replace(run_inputs["result"], acceptance=acceptance, financial_context=None)
    execution = copy.copy(run_inputs["execution"])
    object.__setattr__(execution, "result", result)
    with monkeypatch.context() as blocked:
        calls = _block_snapshot_writes(blocked)
        with pytest.raises(ValueError, match="custom"):
            snapshots.export_baseline_snapshot(execution=execution, output_root=root)
    assert calls == []
    assert {path.relative_to(root) for path in root.rglob("*")} == inventory
    assert {path.relative_to(root): path.read_bytes()
            for path in root.rglob("*") if path.is_file()} == previous_bytes
    if existing_root:
        assert (root / "current.json").read_bytes() == pointer
        assert len(list((root / "runs").iterdir())) == 1
    else:
        assert not root.exists()
        assert not (root / "runs").exists()
        assert not (root / "current.json").exists()
    assert not list(root.rglob(".staging-*"))
    assert not list(root.glob(".current-*.tmp"))


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


def _snapshot_tree_state(root):
    """Capture the complete inventory and file bytes, including a corrupt pointer."""
    return {path.relative_to(root): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


@pytest.mark.parametrize("mutation, expected_exception, expected_error", [
    pytest.param("missing_current_pointer", FileNotFoundError, r"current\.json",
                 id="missing_current_pointer"),
    pytest.param("invalid_current_json", json.JSONDecodeError,
                 "Expecting property name enclosed in double quotes", id="invalid_current_json"),
    pytest.param("malformed_pointer_run_id", ValueError, r"^Invalid snapshot pointer\.$",
                 id="malformed_pointer_run_id"),
    pytest.param("pointer_run_path_mismatch", ValueError, r"^Invalid snapshot pointer\.$",
                 id="pointer_run_path_mismatch"),
    pytest.param("referenced_run_absent", FileNotFoundError, r"manifest\.json",
                 id="referenced_run_absent"),
    pytest.param("manifest_raw_sha_mismatch", ValueError, r"^Snapshot manifest checksum mismatch\.$",
                 id="manifest_raw_sha_mismatch"),
    pytest.param("manifest_run_id_mismatch", ValueError, r"^Invalid snapshot manifest\.$",
                 id="manifest_run_id_mismatch"),
    pytest.param("manifest_not_accepted", ValueError, r"^Invalid snapshot manifest\.$",
                 id="manifest_not_accepted"),
    pytest.param("manifest_inventory_missing", ValueError, r"^Invalid snapshot manifest\.$",
                 id="manifest_inventory_missing"),
    pytest.param("manifest_inventory_extra", ValueError, r"^Invalid snapshot manifest\.$",
                 id="manifest_inventory_extra"),
    pytest.param("metadata_created_at_mismatch", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="metadata_created_at_mismatch"),
    pytest.param("metadata_status_mismatch", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="metadata_status_mismatch"),
    pytest.param("metadata_historical_acceptance_false", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="metadata_historical_acceptance_false"),
    pytest.param("pointer_execution_sha_mismatch", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="pointer_execution_sha_mismatch"),
    pytest.param("manifest_execution_sha_mismatch", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="manifest_execution_sha_mismatch"),
    pytest.param("metadata_execution_sha_mismatch", ValueError,
                 r"^Snapshot metadata does not describe an accepted run\.$", id="metadata_execution_sha_mismatch"),
])
def test_current_reader_rejects_invalid_pointer_manifest_or_metadata_without_fallback(
    run_inputs, tmp_path, mutation, expected_exception, expected_error,
):
    execution = run_inputs["execution"]
    first = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    second = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    assert first.published is True
    assert second.published is True
    assert first.run_id != second.run_id
    for exported in (first, second):
        _assert_complete_run_archive(exported.run_path, execution=execution, accepted=True)
    assert snapshots.resolve_current_snapshot(tmp_path) == second.run_path
    first_bytes = _snapshot_tree_state(first.run_path)

    pointer_path = tmp_path / "current.json"
    manifest_path = second.run_path / "manifest.json"
    metadata_path = second.run_path / "metadata.json"
    pointer = json.loads(pointer_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    invalid_sha = "0" * 64
    assert invalid_sha != execution.binding_sha256
    absent_run = tmp_path / "runs" / ("0" * 32)
    assert not absent_run.exists()

    if mutation == "missing_current_pointer":
        pointer_path.unlink()
    elif mutation == "invalid_current_json":
        pointer_path.write_text("{")
    elif mutation in {"malformed_pointer_run_id", "pointer_run_path_mismatch",
                      "referenced_run_absent", "pointer_execution_sha_mismatch"}:
        if mutation == "malformed_pointer_run_id":
            pointer["run_id"] = "invalid-run-id"
        elif mutation == "pointer_run_path_mismatch":
            pointer["run_path"] = f"runs/{first.run_id}"
        elif mutation == "referenced_run_absent":
            pointer["run_id"] = absent_run.name
            pointer["run_path"] = f"runs/{absent_run.name}"
        else:
            pointer["execution_binding_sha256"] = invalid_sha
        pointer_path.write_text(json.dumps(pointer))
    elif mutation == "manifest_raw_sha_mismatch":
        # Keep JSON and all declarations valid; do not repair the raw SHA under test.
        manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    elif mutation.startswith("manifest_"):
        if mutation == "manifest_run_id_mismatch":
            manifest["run_id"] = first.run_id
        elif mutation == "manifest_not_accepted":
            manifest["accepted_for_use"] = False
        elif mutation == "manifest_inventory_missing":
            del manifest["files_sha256"]["calendar.json"]
        elif mutation == "manifest_inventory_extra":
            manifest["files_sha256"]["unexpected.json"] = invalid_sha
        else:
            assert mutation == "manifest_execution_sha_mismatch"
            manifest["execution_binding_sha256"] = invalid_sha
        # Only repair the enclosing manifest SHA, never its inventory or execution SHA.
        manifest_path.write_text(json.dumps(manifest))
        pointer["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        pointer_path.write_text(json.dumps(pointer))
    else:
        if mutation == "metadata_created_at_mismatch":
            metadata["created_at_utc"] = "2000-01-01T00:00:00+00:00"
            assert metadata["created_at_utc"] != manifest["created_at_utc"]
        elif mutation == "metadata_status_mismatch":
            metadata["status"] = "rejected"
        elif mutation == "metadata_historical_acceptance_false":
            metadata["acceptance"]["accepted_for_use"] = False
        else:
            assert mutation == "metadata_execution_sha_mismatch"
            metadata["execution_binding_sha256"] = invalid_sha
        metadata_path.write_text(json.dumps(metadata))
        _rehash(second.run_path, tmp_path)

    # Compare the corrupt state immediately around the read, not against initial setup.
    before_read = _snapshot_tree_state(tmp_path)
    with pytest.raises(expected_exception, match=expected_error) as error:
        snapshots.resolve_current_snapshot(tmp_path)
    assert _snapshot_tree_state(tmp_path) == before_read
    if mutation == "missing_current_pointer":
        assert error.value.filename == str(pointer_path)
    elif mutation == "referenced_run_absent":
        assert error.value.filename == str(absent_run / "manifest.json")
    elif mutation == "invalid_current_json":
        assert error.value.doc == "{"
    assert first.run_path.is_dir()
    assert second.run_path.is_dir()
    assert _snapshot_tree_state(first.run_path) == first_bytes
    _assert_complete_run_archive(first.run_path, execution=execution, accepted=True)


@pytest.mark.parametrize("mutation, expected_error", [
    pytest.param("unsupported_construction_flag", r"^Unsupported baseline policy identity\.$",
                 id="unsupported_construction_flag"),
    pytest.param("missing_historical_policy_field", r"^Unsupported baseline policy identity\.$",
                 id="missing_historical_policy_field"),
    pytest.param("custom_historical_acceptance",
                 r"^Snapshot standard acceptance policy binding mismatch\.$", id="custom_historical_acceptance"),
])
def test_assurance_rejects_unsupported_historical_policy_after_outer_integrity_passes(
    run_inputs, tmp_path, monkeypatch, mutation, expected_error,
):
    import copy
    from yield_curves import baseline, pricing, repricing, snapshot_assurance

    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert exported.published is True
    metadata_path = exported.run_path / "metadata.json"
    manifest_path = exported.run_path / "manifest.json"
    pointer_path = tmp_path / "current.json"
    metadata = json.loads(metadata_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    pointer = json.loads(pointer_path.read_text())
    original = copy.deepcopy(metadata)
    execution = metadata["execution"]
    policy = execution["financial_context"]["policy"]
    historical = execution["acceptance"]
    payload_bytes = {name: (exported.run_path / name).read_bytes()
                     for name in manifest["files_sha256"] if name != "metadata.json"}

    if mutation == "custom_historical_acceptance":
        descriptor = historical["acceptance_policy"]
        assert descriptor["pass_tolerance_bp"] == 0.01
        assert descriptor["fail_tolerance_bp"] == 0.10
        descriptor.update(kind="CUSTOM_ANALYTICAL_ASSESSMENT", identifier=None)
        metadata["acceptance"] = copy.deepcopy(historical)
        metadata["acceptance_sha256"] = workflow.fingerprint(historical)
        assert policy == original["execution"]["financial_context"]["policy"]
    else:
        assert policy["extrapolation"] is False
        if mutation == "unsupported_construction_flag":
            policy["extrapolation"] = True
        else:
            assert mutation == "missing_historical_policy_field"
            del policy["extrapolation"]
        metadata["financial_context_sha256"] = workflow.fingerprint(execution["financial_context"])
        assert historical == original["execution"]["acceptance"]
    for field in ("baseline_identifier", "calibration_approach", "interpolation_method"):
        assert policy[field] == original["execution"]["financial_context"]["policy"][field]
    assert historical["binding"] == original["execution"]["acceptance"]["binding"]
    assert metadata["payload_sha256"] == original["payload_sha256"]

    execution_sha = workflow.fingerprint(execution)
    for path, record in ((metadata_path, metadata), (manifest_path, manifest), (pointer_path, pointer)):
        record["execution_binding_sha256"] = execution_sha
        path.write_text(json.dumps(record))
    _rehash(exported.run_path, tmp_path)
    assert {name: (exported.run_path / name).read_bytes() for name in payload_bytes} == payload_bytes

    before_read = _snapshot_tree_state(tmp_path)
    assert snapshots.resolve_current_snapshot(tmp_path) == exported.run_path
    repricing_calls = []

    def forbidden_repricing(*args, **kwargs):
        repricing_calls.append(True)
        pytest.fail("Historical policy must be rejected before independent repricing")

    with monkeypatch.context() as blocked:
        # Cover the baseline entrypoint and par-rate function at their effective aliases.
        functions = (baseline._independently_reprice, repricing.calculate_par_rate)
        for module in (baseline, pricing, repricing, snapshot_assurance):
            for name, value in tuple(vars(module).items()):
                if any(value is function for function in functions):
                    blocked.setattr(module, name, forbidden_repricing)
        with pytest.raises(ValueError, match=expected_error):
            snapshot_assurance.assess_current_snapshot(tmp_path)
    assert repricing_calls == []
    assert _snapshot_tree_state(tmp_path) == before_read


def test_assurance_reconstructs_payload_binding_after_node_zero_check_passes(
    run_inputs, tmp_path, monkeypatch,
):
    from math import isfinite
    from yield_curves import baseline, snapshot_assurance
    from yield_curves.curves import CubicContinuousZeroCurve

    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert exported.published is True
    original_tree = _snapshot_tree_state(tmp_path)
    metadata_path = exported.run_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    historical_binding = metadata["execution"]["acceptance"]["binding"]
    nodes_path = exported.run_path / "curve_nodes.csv"
    with nodes_path.open(newline="") as file:
        reader = csv.DictReader(file)
        header, rows = reader.fieldnames, list(reader)
    original_rows = [dict(row) for row in rows]
    rows[0]["discount_factor"] = str(float(rows[0]["discount_factor"]) * 0.999)
    discount_factors = tuple(float(row["discount_factor"]) for row in rows)
    assert all(isfinite(df) and df > 0 for df in discount_factors)
    assert discount_factors[0] != float(original_rows[0]["discount_factor"])
    curve = CubicContinuousZeroCurve(
        reference_date=date.fromisoformat(metadata["curve_reference_date"]),
        node_dates=tuple(date.fromisoformat(row["pillar_date"]) for row in rows),
        discount_factors=discount_factors,
    )
    # Match the exact float evaluations used by reconstruction, including rounding.
    # The binding oracle remains the untouched historical identity, not this curve.
    for row, day in zip(rows, curve.node_dates, strict=True):
        row["continuous_zero_rate"] = str(curve.zero_rate(day))
    with nodes_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    _rehash(exported.run_path, tmp_path)

    with nodes_path.open(newline="") as file:
        serialized_rows = list(csv.DictReader(file))
    assert [(row["tenor"], row["pillar_date"]) for row in serialized_rows] == [
        (row["tenor"], row["pillar_date"]) for row in original_rows
    ]
    reconstructed = CubicContinuousZeroCurve(
        reference_date=curve.reference_date,
        node_dates=tuple(date.fromisoformat(row["pillar_date"]) for row in serialized_rows),
        discount_factors=tuple(float(row["discount_factor"]) for row in serialized_rows),
    )
    assert all(float(row["continuous_zero_rate"]) == reconstructed.zero_rate(day)
               for row, day in zip(serialized_rows, reconstructed.node_dates, strict=True))
    assert json.loads(metadata_path.read_text()) == metadata
    assert json.loads(metadata_path.read_text())["execution"]["acceptance"]["binding"] == historical_binding
    before_read = _snapshot_tree_state(tmp_path)
    assert before_read.keys() == original_tree.keys()
    assert {path for path in original_tree if before_read[path] != original_tree[path]} == {
        nodes_path.relative_to(tmp_path),
        (exported.run_path / "manifest.json").relative_to(tmp_path), Path("current.json"),
    }
    assert snapshots.resolve_current_snapshot(tmp_path) == exported.run_path
    repricing_calls = []

    def forbidden_repricing(*args, **kwargs):
        repricing_calls.append((args, kwargs))
        pytest.fail("Payload binding must be checked before independent repricing")

    original_reprice = baseline._independently_reprice
    with monkeypatch.context() as blocked:
        for module in (baseline, snapshot_assurance):
            for name, value in tuple(vars(module).items()):
                if value is original_reprice:
                    blocked.setattr(module, name, forbidden_repricing)
        with pytest.raises(ValueError) as error:
            snapshot_assurance.assess_current_snapshot(tmp_path)
    assert str(error.value) == "Snapshot curve / payload / acceptance binding mismatch."
    assert repricing_calls == []
    assert _snapshot_tree_state(tmp_path) == before_read


@pytest.mark.parametrize("variant, expected_error", [
    pytest.param("fresh_history",
                 "Snapshot independent repricing / historical acceptance binding mismatch.",
                 id="fresh_history"),
    pytest.param("repricing_artifact", "Snapshot repricing artifact binding mismatch.",
                 id="repricing_artifact"),
])
def test_assurance_rejects_fresh_history_or_repricing_artifact_mismatch(
    run_inputs, tmp_path, monkeypatch, variant, expected_error,
):
    from yield_curves import baseline, repricing, snapshot_assurance

    execution = run_inputs["execution"]
    exported = snapshots.export_baseline_snapshot(execution=execution, output_root=tmp_path)
    assert exported.published is True
    original_tree = _snapshot_tree_state(tmp_path)
    metadata_path = exported.run_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    historical = metadata["execution"]["acceptance"]
    historical_binding = historical["binding"]
    assert historical["accepted_for_use"] is True
    target_quote = next(quote for quote in execution.inputs.quotes if quote.tenor == "1M")

    if variant == "repricing_artifact":
        path = exported.run_path / "quote_repricing.csv"
        with path.open(newline="") as file:
            reader = csv.DictReader(file)
            header, rows = reader.fieldnames, list(reader)
        original_rows = [dict(row) for row in rows]
        target_row = next(row for row in rows if row["tenor"] == target_quote.tenor)
        target_row["repriced_quote"] = str(float(target_row["repriced_quote"]) + 0.001)
        assert target_row["repriced_quote"] != next(
            row["repriced_quote"] for row in original_rows if row["tenor"] == target_quote.tenor
        )
        assert [{k: v for k, v in row.items() if k != "repriced_quote"} for row in rows] == [
            {k: v for k, v in row.items() if k != "repriced_quote"} for row in original_rows
        ]
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)
        _rehash(exported.run_path, tmp_path)

    before_read = _snapshot_tree_state(tmp_path)
    assert before_read.keys() == original_tree.keys()
    changed = {path for path in original_tree if before_read[path] != original_tree[path]}
    assert changed == (set() if variant == "fresh_history" else {
        (exported.run_path / "quote_repricing.csv").relative_to(tmp_path),
        (exported.run_path / "manifest.json").relative_to(tmp_path), Path("current.json"),
    })
    assert snapshots.resolve_current_snapshot(tmp_path) == exported.run_path
    original_reprice = baseline._independently_reprice
    original_par_rate = repricing.calculate_par_rate
    repricing_calls, repricing_results, pricing_calls = [], [], []
    delta = 1e-7  # Decimal rate: 0.001 bp, below the STANDARD PASS threshold.

    def reprice(**kwargs):
        repricing_calls.append(kwargs)
        result = original_reprice(**kwargs)
        repricing_results.append(result)
        return result

    def perturbed_par_rate(*, ois, projection_curve, discount_curve):
        rate = original_par_rate(ois=ois, projection_curve=projection_curve, discount_curve=discount_curve)
        adjusted = rate + delta if ois.contractual_maturity_date == target_quote.contractual_maturity_date else rate
        pricing_calls.append((ois.contractual_maturity_date, rate, adjusted))
        return adjusted

    with monkeypatch.context() as patched:
        for module in (baseline, snapshot_assurance):
            for name, value in tuple(vars(module).items()):
                if value is original_reprice:
                    patched.setattr(module, name, reprice)
        if variant == "fresh_history":
            # Effective alias used inside reprice_calibration_instruments.
            patched.setattr(repricing, "calculate_par_rate", perturbed_par_rate)
        with pytest.raises(ValueError) as error:
            snapshot_assurance.assess_current_snapshot(tmp_path)

    assert str(error.value) == expected_error
    assert len(repricing_calls) == len(repricing_results) == 1
    arguments = repricing_calls[0]
    calibration = arguments["calibration_result"]
    assert calibration.success is True
    assert calibration.curve.reference_date == execution.inputs.reference_date
    assert calibration.curve.node_dates == execution.inputs.pillar_dates
    assert calibration.curve.discount_factors == execution.result.curve.discount_factors
    assert tuple(arguments["quotes"]) == execution.inputs.quotes
    assert arguments["calendar"] == execution.inputs.calendar.to_calendar()
    assert arguments["pass_tolerance_bp"] == historical["pass_tolerance_bp"]
    assert arguments["fail_tolerance_bp"] == historical["fail_tolerance_bp"]
    checks, issues = repricing_results[0]
    assert issues == ()
    assert len(checks) == len(execution.inputs.quotes)
    assert all(check.status is repricing.InstrumentValidationStatus.PASS for check in checks)
    assert all(check.absolute_error_bp <= arguments["pass_tolerance_bp"] for check in checks)
    if variant == "fresh_history":
        assert [maturity for maturity, _, _ in pricing_calls] == [
            quote.contractual_maturity_date for quote in execution.inputs.quotes
        ]
        assert sum(maturity == target_quote.contractual_maturity_date for maturity, _, _ in pricing_calls) == 1
        for maturity, rate, adjusted in pricing_calls:
            if maturity == target_quote.contractual_maturity_date:
                assert adjusted == rate + delta
                assert adjusted != rate
            else:
                assert adjusted == rate
        assert workflow.json_value(checks) != historical["checks"]
    else:
        assert pricing_calls == []
        assert workflow.json_value(checks) == historical["checks"]
    after_metadata = json.loads(metadata_path.read_text())
    assert after_metadata == metadata
    assert after_metadata["execution"]["acceptance"] == historical
    assert after_metadata["execution"]["acceptance"]["binding"] == historical_binding
    assert _snapshot_tree_state(tmp_path) == before_read


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
    previous_bytes = {path.name: path.read_bytes() for path in first.run_path.iterdir()}
    previous_runs = set((tmp_path / "runs").iterdir())
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
    assert {path.name: path.read_bytes() for path in first.run_path.iterdir()} == previous_bytes
    new_runs = set((tmp_path / "runs").iterdir()) - previous_runs
    if phase in {"staging_sync", "rename"}:
        assert new_runs == set()
    else:
        assert len(new_runs) == 1
        new_run = new_runs.pop()
        _assert_complete_run_archive(new_run, execution=run_inputs["execution"], accepted=True)
        if after_commit:
            assert current == new_run


def test_assurance_reprices_without_solver_or_any_write(run_inputs, tmp_path, monkeypatch):
    import builtins
    import io
    import os
    import scipy.optimize as optimize
    from yield_curves import baseline, bootstrap, calibration, snapshot_assurance as assurance

    exported = snapshots.export_baseline_snapshot(execution=run_inputs["execution"], output_root=tmp_path)
    assert exported.published is True
    assert snapshots.resolve_current_snapshot(tmp_path) == exported.run_path
    before_read = _snapshot_tree_state(tmp_path)
    forbidden_calls, repricing_calls = [], []
    original_reprice = baseline._independently_reprice

    def reprice(**kwargs):
        repricing_calls.append(kwargs)
        return original_reprice(**kwargs)

    def sentinel(location):
        def forbidden(*args, **kwargs):
            forbidden_calls.append(location)
            pytest.fail(f"Assurance attempted forbidden operation: {location}")
        return forbidden

    def readonly_open(original, location):
        def readonly(file, mode="r", *args, **kwargs):
            if any(char in mode for char in "wax+"):
                return sentinel(location)(file, mode, *args, **kwargs)
            return original(file, mode, *args, **kwargs)
        return readonly

    original_os_open = os.open
    write_flags = os.O_CREAT | os.O_TRUNC | os.O_APPEND
    # O_TMPFILE also creates a writable file without a directory entry.
    temporary_flag = getattr(os, "O_TMPFILE", 0)

    def readonly_os_open(path, flags, mode=0o777, *, dir_fd=None):
        if ((flags & os.O_ACCMODE) in (os.O_WRONLY, os.O_RDWR)
                or flags & write_flags
                or (temporary_flag and flags & temporary_flag == temporary_flag)):
            return sentinel("os.open")(path, flags, mode, dir_fd=dir_fd)
        return original_os_open(path, flags, mode, dir_fd=dir_fd)

    forbidden_functions = (
        bootstrap.bootstrap_ftiie_ois_curve,
        bootstrap.bootstrap_ftiie_ois_curve_with_method,
        calibration.calibrate_ftiie_ois_curve_simultaneously,
        optimize.brentq, optimize.least_squares,
        workflow.build_baseline_execution, baseline.build_baseline_ftiie_curve,
        snapshots.export_baseline_snapshot,
    )
    # Capture all originals before patching shared modules or Path methods.
    replacements = [(function, sentinel(function.__name__)) for function in forbidden_functions]
    replacements.extend((getattr(owner, name), sentinel(f"{owner.__name__}.{name}"))
                        for owner, names in (
                            (os, ("mkdir", "makedirs", "unlink", "remove", "rmdir", "rename", "replace")),
                            (Path, ("mkdir", "unlink", "rmdir", "rename", "replace")),
                            (snapshots.tempfile, ("mkdtemp",)),
                        ) for name in names)
    replacements.extend([
        (builtins.open, readonly_open(builtins.open, "builtins.open")),
        (io.open, readonly_open(io.open, "io.open")),
        (original_os_open, readonly_os_open),
        (original_reprice, reprice),
    ])
    targets = []
    for owner in (baseline, bootstrap, calibration, workflow, snapshots, assurance,
                  optimize, builtins, io, os, Path, snapshots.tempfile):
        for name, value in tuple(vars(owner).items()):
            for original, replacement in replacements:
                if value is original:
                    targets.append((owner, name, replacement))
                    break

    with monkeypatch.context() as blocked:
        # Includes definition-time aliases, even in the reader and assurance.
        for owner, name, replacement in targets:
            blocked.setattr(owner, name, replacement)
        assessment = assurance.assess_current_snapshot(tmp_path)

    # All global entrypoints are restored before filesystem checks and teardown.
    assert assessment.accepted_for_use is True
    assert len(repricing_calls) == 1
    assert forbidden_calls == []
    assert _snapshot_tree_state(tmp_path) == before_read


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
