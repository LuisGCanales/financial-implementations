from pathlib import Path

import pytest

from yield_curves.project_paths import find_project_root


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_find_project_root_accepts_file_and_directory_paths() -> None:
    assert find_project_root(PROJECT_ROOT / "scripts") == PROJECT_ROOT
    assert (
        find_project_root(
            PROJECT_ROOT
            / "scripts"
            / "experiments"
            / "future_script.py"
        )
        == PROJECT_ROOT
    )


def test_find_project_root_fails_without_project_markers(
    tmp_path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Could not locate",
    ):
        find_project_root(tmp_path / "missing.py")
