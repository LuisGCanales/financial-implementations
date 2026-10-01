"""Characterize plot helpers without importing or running artifact producers."""

import ast
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = {
    "synthetic": ("synthetic/plot_synthetic_reference_data.py", "build_dense_curve_grid", "year_fraction_act_360", list),
    "bootstrap": ("bootstrap/plot_bootstrap_recovery.py", "build_date_grid", "year_fraction_act_360", list),
    "two_method": ("interpolation/plot_interpolation_method_comparison.py", "build_date_grid", "act_360", tuple),
    "three_method": ("interpolation/plot_three_interpolation_methods.py", "build_date_grid", "act_360", tuple),
    "heatmaps": ("sensitivity/plot_global_forward_sensitivity_heatmaps.py", None, "act_360", None),
}
GRID_SCRIPTS = tuple(name for name, spec in SCRIPTS.items() if spec[1])
REFERENCE = date(2026, 1, 1)


def load_helpers(name):
    """Execute only helper definitions, their shared import and default constant."""
    relative, grid, conversion, _ = SCRIPTS[name]
    path = ROOT / "scripts/experiments" / relative
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in {grid, conversion}
        or isinstance(node, ast.ImportFrom) and node.module == "yield_curves.date_grids"
        or isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "DENSE_GRID_STEP_DAYS"
            for target in node.targets
        )
    )]
    namespace = {"date": date, "timedelta": timedelta}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("name", GRID_SCRIPTS)
@pytest.mark.parametrize("horizon,step,offsets", [
    (14, 7, (0, 7, 14)), (15, 7, (0, 7, 14, 15)),
    (0, 7, (0,)), (1, 7, (0, 1)), (6, 7, (0, 6)),
    (7, 7, (0, 7)), (3, 1, (0, 1, 2, 3)),
])
def test_grid_endpoints_types_and_order(name, horizon, step, offsets):
    helper = load_helpers(name)[SCRIPTS[name][1]]
    result = helper(start_date=REFERENCE, end_date=REFERENCE + timedelta(days=horizon),
                    step_days=step)
    assert type(result) is SCRIPTS[name][3]
    assert tuple(result) == tuple(REFERENCE + timedelta(days=n) for n in offsets)
    assert all(type(item) is date for item in result)


@pytest.mark.parametrize("name", GRID_SCRIPTS)
@pytest.mark.parametrize("horizon,step,message", [
    (0, 0, "Grid step must be positive."),
    (-1, -1, "Grid step must be positive."),
    (-1, 7, "End date cannot precede start date."),
])
def test_grid_guard_order_and_messages(name, horizon, step, message):
    helper = load_helpers(name)[SCRIPTS[name][1]]
    with pytest.raises(ValueError) as error:
        helper(start_date=REFERENCE, end_date=REFERENCE + timedelta(days=horizon),
               step_days=step)
    assert str(error.value) == message


@pytest.mark.parametrize("name", GRID_SCRIPTS)
def test_grid_default_keyword_only_and_date_limit(name):
    helper = load_helpers(name)[SCRIPTS[name][1]]
    assert tuple(helper(start_date=REFERENCE, end_date=REFERENCE + timedelta(days=8))) == (
        REFERENCE, REFERENCE + timedelta(days=7), REFERENCE + timedelta(days=8),
    )
    with pytest.raises(TypeError):
        helper(REFERENCE, REFERENCE)
    assert tuple(helper(start_date=date.max, end_date=date.max)) == (date.max,)
    with pytest.raises(OverflowError):
        helper(start_date=date.max - timedelta(days=1), end_date=date.max)


@pytest.mark.parametrize("name", GRID_SCRIPTS)
def test_forward_starts_keep_off_step_terminal(name):
    helper = load_helpers(name)[SCRIPTS[name][1]]
    horizon = REFERENCE + timedelta(days=43)
    last_start = horizon - timedelta(days=28)
    starts = helper(start_date=REFERENCE, end_date=last_start)
    assert tuple(starts) == tuple(REFERENCE + timedelta(days=n) for n in (0, 7, 14, 15))
    assert starts[-1] + timedelta(days=28) == horizon


@pytest.mark.parametrize("name", SCRIPTS)
@pytest.mark.parametrize("offset", [-360, -1, 0, 1, 360])
def test_presentation_act360_remains_signed(name, offset):
    helper = load_helpers(name)[SCRIPTS[name][2]]
    result = helper(REFERENCE, REFERENCE + timedelta(days=offset))
    assert type(result) is float
    assert result == offset / 360.0
    keywords = (dict(start=REFERENCE, end=REFERENCE + timedelta(days=offset))
                if name == "synthetic" else
                dict(reference_date=REFERENCE, target_date=REFERENCE + timedelta(days=offset))
                if name == "heatmaps" else
                dict(start_date=REFERENCE, end_date=REFERENCE + timedelta(days=offset)))
    assert helper(**keywords) == result
