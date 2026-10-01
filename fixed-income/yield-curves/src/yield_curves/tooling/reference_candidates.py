"""Exclusive candidate output for repository reference-maintenance tools."""

from pathlib import Path


FROZEN_REFERENCES = (
    "tests/fixtures/ftiie_baseline_reference_v1.json",
    "data/synthetic/ftiie_ois_quotes_v1.csv",
)


def validate_candidate_path(path: Path, *, root: Path) -> None:
    """Reject canonical paths (including aliases), and every existing entry."""
    if path.resolve() in {(root / name).resolve() for name in FROZEN_REFERENCES}:
        raise ValueError("Frozen reference destination is forbidden; choose a candidate path.")
    if path.exists() or path.is_symlink():
        raise ValueError("Output already exists; choose a new candidate path.")


def write_candidate(path: Path, payload: bytes, *, root: Path) -> None:
    """Never truncate an existing destination, even if created after preflight."""
    validate_candidate_path(path, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(payload)
