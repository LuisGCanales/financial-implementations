"""Utilities for reproducible analytical-report outputs.

Reporting artifacts are separated into:

    figures/
    tables/
    text/
    metadata/

under the project-level reports directory.

These helpers deliberately contain no financial logic.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence


ReportCategory = Literal[
    "figures",
    "tables",
    "text",
    "metadata",
]


PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

REPORTS_ROOT = (
    PROJECT_ROOT
    / "reports"
)


def build_report_path(
    *,
    category: ReportCategory,
    section: str,
    stem: str,
    suffix: str,
    reports_root: Path | None = None,
) -> Path:
    """Build and create one report-output path."""

    root = (
        REPORTS_ROOT
        if reports_root is None
        else reports_root
    )

    suffix = suffix.lstrip(".")

    directory = (
        root
        / category
        / section
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        directory
        / f"{stem}.{suffix}"
    )


def save_figure(
    *,
    fig,
    section: str,
    stem: str,
    formats: Sequence[str] = (
        "png",
        "svg",
    ),
    dpi: int = 200,
    reports_root: Path | None = None,
) -> tuple[Path, ...]:
    """Save one matplotlib-like figure in multiple formats."""

    paths: list[Path] = []

    for format_name in formats:
        path = build_report_path(
            category="figures",
            section=section,
            stem=stem,
            suffix=format_name,
            reports_root=reports_root,
        )

        kwargs: dict[str, Any] = {
            "bbox_inches": "tight",
        }

        if format_name.lower() in {
            "png",
            "jpg",
            "jpeg",
        }:
            kwargs["dpi"] = dpi

        fig.savefig(
            path,
            **kwargs,
        )

        paths.append(
            path
        )

    return tuple(
        paths
    )


def save_csv(
    *,
    section: str,
    stem: str,
    header: Sequence[str],
    rows: Iterable[Sequence[Any]],
    reports_root: Path | None = None,
) -> Path:
    """Save machine-readable tabular output."""

    path = build_report_path(
        category="tables",
        section=section,
        stem=stem,
        suffix="csv",
        reports_root=reports_root,
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(
            file
        )

        writer.writerow(
            header
        )

        writer.writerows(
            rows
        )

    return path


def save_text_report(
    *,
    section: str,
    stem: str,
    text: str,
    reports_root: Path | None = None,
) -> Path:
    """Save human-readable text report."""

    path = build_report_path(
        category="text",
        section=section,
        stem=stem,
        suffix="txt",
        reports_root=reports_root,
    )

    if not text.endswith("\n"):
        text += "\n"

    path.write_text(
        text,
        encoding="utf-8",
    )

    return path


def save_json(
    *,
    section: str,
    stem: str,
    data: Any,
    reports_root: Path | None = None,
) -> Path:
    """Save experiment metadata or structured diagnostics."""

    path = build_report_path(
        category="metadata",
        section=section,
        stem=stem,
        suffix="json",
        reports_root=reports_root,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            sort_keys=True,
            default=str,
        )

        file.write(
            "\n"
        )

    return path


class TextReport:
    """Small line-oriented text-report builder."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def line(
        self,
        text: str = "",
    ) -> None:
        self._lines.append(
            str(text)
        )

    def rule(
        self,
        *,
        character: str = "-",
        width: int = 80,
    ) -> None:
        self.line(
            character * width
        )

    def render(self) -> str:
        return (
            "\n".join(
                self._lines
            ).rstrip()
            + "\n"
        )

    def save(
        self,
        *,
        section: str,
        stem: str,
        echo: bool = True,
        reports_root: Path | None = None,
    ) -> Path:
        text = self.render()

        if echo:
            print(
                text,
                end="",
            )

        return save_text_report(
            section=section,
            stem=stem,
            text=text,
            reports_root=reports_root,
        )