"""Enforce import direction; research may consume core, never the reverse."""

import ast
import importlib
from importlib.util import resolve_name
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src/yield_curves"
OPERATIONAL = {"baseline", "inputs", "snapshots", "snapshot_assurance", "quote_io"}
CORE = {"bootstrap", "calibration", "calendars", "conventions", "curves",
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
                 PACKAGE / "tooling/cli_inputs.py"]:
        source = path.read_text()
        assert "research" not in source
        assert "find_project_root" not in source
        assert "data/synthetic" not in source
