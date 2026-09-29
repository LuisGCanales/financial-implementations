"""Project-root path utilities for scripts and local tooling."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start_path: Path) -> Path:
    """Find the yield-curves project root from a file or directory path."""

    path = start_path.expanduser().resolve()
    starting_directory = path if path.is_dir() else path.parent

    for candidate in (
        starting_directory,
        *starting_directory.parents,
    ):
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src" / "yield_curves").is_dir()
        ):
            return candidate

    raise FileNotFoundError(
        "Could not locate the yield-curves project root from "
        f"{start_path!s}."
    )