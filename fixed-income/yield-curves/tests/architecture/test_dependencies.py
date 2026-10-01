"""Enforce import direction; research may consume core, never the reverse."""

import ast
import importlib
from importlib.util import resolve_name
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src/yield_curves"
OPERATIONAL = {"baseline", "inputs", "snapshots", "snapshot_assurance", "quote_io", "calendar_io", "execution"}
ENGINES = {"bootstrap", "calibration", "engine_capabilities"}
CORE = {"engine_capabilities", "bootstrap", "calibration", "calendars", "conventions", "curves",
        "diagnostics", "log_linear_diagnostics", "instruments", "observations",
        "pricing", "quotes", "repricing", "schedules", "tenors"}


def _imports(path):
    relative = path.relative_to(ROOT / "src").with_suffix("")
    parts = list(relative.parts)
    package = ".".join(parts[:-1])
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            module = resolve_name(name, package) if node.level else name
            yield module
            yield from (module + "." + alias.name for alias in node.names)


def test_package_layers_are_explicit_and_imports_point_inward():
    files = list(PACKAGE.rglob("*.py"))
    modules = {".".join(p.relative_to(ROOT / "src").with_suffix("").parts).removesuffix(".__init__"): p
               for p in files}
    graph = {name: {target for target in _imports(path) if target in modules}
             for name, path in modules.items()}
    for name in graph:
        if name == "yield_curves":
            continue
        layer = name.split(".")[1]
        assert layer in CORE | OPERATIONAL | {"research", "tooling"}, name
    for start in graph:
        if start != "yield_curves" and start.split(".")[1] not in CORE | OPERATIONAL:
            continue
        visited, pending = set(), [start]
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            assert not name.startswith(("yield_curves.research", "yield_curves.tooling")), (start, name)
            if start.split(".")[-1] in CORE:
                assert name.split(".")[-1] not in OPERATIONAL, (start, name)
            if start in {f"yield_curves.{layer}" for layer in CORE | {"baseline", "inputs"}}:
                assert name not in {"yield_curves.calendar_io", "yield_curves.quote_io",
                                    "yield_curves.execution", "yield_curves.snapshots",
                                    "yield_curves.snapshot_assurance"}, (start, name)
            if start == "yield_curves.curves":
                assert name not in {f"yield_curves.{engine}" for engine in ENGINES}, (start, name)
            if start == "yield_curves.engine_capabilities":
                assert name not in {"yield_curves.bootstrap", "yield_curves.calibration"}, (start, name)
            pending.extend(graph[name] - visited)


def test_baseline_import_does_not_load_research_or_local_tooling():
    subprocess.run([sys.executable, "-c", "import sys; import yield_curves.baseline; "
                    "assert not any(n.startswith(('yield_curves.research', 'yield_curves.tooling')) "
                    "for n in sys.modules)"], check=True, cwd=ROOT)


def test_all_script_package_imports_resolve_without_executing_scripts():
    for path in (ROOT / "scripts").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("yield_curves"):
                module = importlib.import_module(node.module)
                for alias in node.names:
                    assert hasattr(module, alias.name), (path, node.module, alias.name)


def test_operational_entrypoints_have_no_research_or_repository_defaults():
    for path in [ROOT / "scripts/operational/build_baseline_curve.py",
                 ROOT / "scripts/assurance/validate_baseline_curve.py",
                 PACKAGE / "tooling/cli_inputs.py", PACKAGE / "execution.py"]:
        source = path.read_text()
        assert "research" not in source
        assert "find_project_root" not in source
        assert "data/synthetic" not in source



def test_calendar_domain_has_no_io_imports_or_loader_reexports():
    imports = set(_imports(PACKAGE / "calendars.py"))
    allowed = {"__future__", "dataclasses", "datetime", "enum", "typing",
               "yield_curves.conventions"}
    assert all(any(name == base or name.startswith(base + ".") for base in allowed)
               for name in imports), imports
    tree = ast.parse((PACKAGE / "calendars.py").read_text())
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id in {"open", "__import__"} for node in ast.walk(tree))
    calendar = importlib.import_module("yield_curves.calendars")
    for name in ("load_holidays_csv", "build_mxmc_calendar_from_csv", "_parse_holidays_csv"):
        assert not hasattr(calendar, name)


def test_in_memory_baseline_and_projected_calendar_do_not_load_calendar_io():
    subprocess.run([sys.executable, "-c", """
import sys
from datetime import date
from yield_curves.baseline import build_baseline_ftiie_curve
from yield_curves.calendars import BusinessCalendar, CalendarSource
from yield_curves.quotes import OISQuote
from yield_curves.research.calendars import build_projected_mxmc_calendar

calendar = BusinessCalendar(
    "in memory", holidays=frozenset({date(2026, 9, 16)}),
    coverage_start=date(2026, 1, 1), coverage_end=date(2026, 12, 31),
)
quotes = (
    OISQuote("1M", date(2026, 9, 15), date(2026, 10, 18), 0.08),
    OISQuote("3M", date(2026, 9, 15), date(2026, 12, 18), 0.081),
)
result = build_baseline_ftiie_curve(quotes=quotes, calendar=calendar)
assert result.accepted_for_use
projected = build_projected_mxmc_calendar(start_year=2026, end_year=2026)
assert projected.provenance.kind is CalendarSource.PROJECTED
assert projected.provenance.sha256 is None
assert not projected.is_business_day(date(2026, 9, 16))
assert "yield_curves.calendar_io" not in sys.modules
"""], check=True, cwd=ROOT)


def test_financial_context_policy_has_no_filesystem_or_adapter_dependencies():
    for module in CORE | {'inputs', 'baseline'}:
        imports = set(_imports(PACKAGE / (module + '.py')))
        forbidden = ('pathlib', 'os', 'io', 'shutil', 'tempfile', 'json', 'hashlib',
                     'yield_curves.calendar_io',
                     'yield_curves.quote_io', 'yield_curves.execution', 'yield_curves.snapshots',
                     'yield_curves.snapshot_assurance', 'yield_curves.tooling')
        assert not any(name == target or name.startswith(target + '.')
                       for name in imports for target in forbidden)
        tree = ast.parse((PACKAGE / (module + '.py')).read_text())
        assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                       and node.func.id == 'open' for node in ast.walk(tree))


def test_snapshot_assurance_has_no_solver_or_publication_calls():
    tree = ast.parse((PACKAGE / "snapshot_assurance.py").read_text())
    forbidden = {"build_baseline_ftiie_curve", "build_baseline_execution",
                 "calibrate_ftiie_ois_curve_simultaneously", "least_squares",
                 "bootstrap_ftiie_ois_curve", "export_baseline_snapshot"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            assert name not in forbidden



def test_research_comparison_lists_remain_explicit():
    two = ("LOG_LINEAR_DF", "LINEAR_CONTINUOUS_ZERO")
    three = (*two, "CUBIC_CONTINUOUS_ZERO")
    experiments = {
        "interpolation/compare_interpolation_methods.py": two,
        "interpolation/compare_interpolation_methods_by_horizon.py": two,
        "interpolation/compare_three_interpolation_methods.py": three,
        "interpolation/plot_three_interpolation_methods.py": three,
        "sensitivity/report_global_sensitivity.py": three,
        "sensitivity/report_forward_sensitivity_locality.py": three,
        "sensitivity/plot_global_forward_sensitivity_heatmaps.py": three,
    }
    for relative, expected in experiments.items():
        path = ROOT / "scripts/experiments" / relative
        tree = ast.parse(path.read_text())
        assignments = [node.value for node in ast.walk(tree)
                       if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id in {"METHODS", "methods"}
                               for target in node.targets)]
        assert len(assignments) == 1, path
        methods = assignments[0]
        assert isinstance(methods, ast.Tuple), path
        identities = tuple(node.attr if isinstance(node, ast.Attribute) else node.value
                           for node in methods.elts)
        assert identities == expected, path


def test_research_has_no_parallel_neutral_quote_dataclasses():
    from dataclasses import fields
    from yield_curves.quotes import OISQuote

    financial_fields = {'tenor', 'trade_date', 'contractual_maturity_date', 'par_rate'}
    assert {field.name for field in fields(OISQuote)} == financial_fields
    for path in (PACKAGE / 'research').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ClassDef):
                declared = {item.target.id for item in node.body
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)}
                assert declared != financial_fields, (path, node.name)
    for module_name, removed in [
        ('sensitivity', 'PerturbedCalibrationQuote'),
        ('global_sensitivity', 'PerturbedGlobalQuote'),
    ]:
        module = importlib.import_module('yield_curves.research.' + module_name)
        assert not hasattr(module, removed)
