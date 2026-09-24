"""Unit tests for reporting utilities."""

from __future__ import annotations

import csv
import json

import matplotlib.pyplot as plt
import pytest

from yield_curves.reporting import (
    TextReport,
    build_report_path,
    save_csv,
    save_figure,
    save_json,
    save_matrix_csv,
    save_text_report,
)


def test_build_report_path_creates_directory(
    tmp_path,
) -> None:
    path = build_report_path(
        category="tables",
        section="test_section",
        stem="example",
        suffix="csv",
        reports_root=tmp_path,
    )

    assert path == (
        tmp_path
        / "tables"
        / "test_section"
        / "example.csv"
    )

    assert path.parent.exists()


def test_build_report_path_accepts_suffix_with_dot(
    tmp_path,
) -> None:
    path = build_report_path(
        category="text",
        section="test_section",
        stem="report",
        suffix=".txt",
        reports_root=tmp_path,
    )

    assert path.name == (
        "report.txt"
    )


def test_save_text_report(
    tmp_path,
) -> None:
    path = save_text_report(
        section="test_section",
        stem="report",
        text="hello",
        reports_root=tmp_path,
    )

    assert path.exists()

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "hello\n"
    )


def test_save_text_report_preserves_existing_newline(
    tmp_path,
) -> None:
    path = save_text_report(
        section="test_section",
        stem="report",
        text="hello\n",
        reports_root=tmp_path,
    )

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "hello\n"
    )


def test_save_csv(
    tmp_path,
) -> None:
    path = save_csv(
        section="test_section",
        stem="table",
        header=(
            "a",
            "b",
        ),
        rows=(
            (1, 2),
            (3, 4),
        ),
        reports_root=tmp_path,
    )

    assert path.exists()

    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.reader(
                file
            )
        )

    assert rows == [
        [
            "a",
            "b",
        ],
        [
            "1",
            "2",
        ],
        [
            "3",
            "4",
        ],
    ]


def test_save_csv_supports_empty_rows(
    tmp_path,
) -> None:
    path = save_csv(
        section="test_section",
        stem="empty_table",
        header=(
            "a",
            "b",
        ),
        rows=(),
        reports_root=tmp_path,
    )

    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.reader(
                file
            )
        )

    assert rows == [
        [
            "a",
            "b",
        ],
    ]


def test_save_json(
    tmp_path,
) -> None:
    path = save_json(
        section="test_section",
        stem="metadata",
        data={
            "method": "test",
            "value": 1,
        },
        reports_root=tmp_path,
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert data == {
        "method": "test",
        "value": 1,
    }


def test_save_json_uses_string_fallback(
    tmp_path,
) -> None:
    class Example:
        def __str__(
            self,
        ) -> str:
            return "example-object"

    path = save_json(
        section="test_section",
        stem="metadata",
        data={
            "object": Example(),
        },
        reports_root=tmp_path,
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert data[
        "object"
    ] == "example-object"


def test_save_matrix_csv(
    tmp_path,
) -> None:
    path = save_matrix_csv(
        section="test_section",
        stem="matrix",
        row_label_name="row",
        row_labels=(
            "A",
            "B",
        ),
        column_labels=(
            "X",
            "Y",
        ),
        matrix=(
            (1.0, 2.0),
            (3.0, 4.0),
        ),
        reports_root=tmp_path,
    )

    assert path.exists()

    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.reader(
                file
            )
        )

    assert rows == [
        [
            "row",
            "X",
            "Y",
        ],
        [
            "A",
            "1.0",
            "2.0",
        ],
        [
            "B",
            "3.0",
            "4.0",
        ],
    ]


def test_save_matrix_csv_supports_empty_matrix(
    tmp_path,
) -> None:
    path = save_matrix_csv(
        section="test_section",
        stem="empty_matrix",
        row_label_name="row",
        row_labels=(),
        column_labels=(
            "X",
            "Y",
        ),
        matrix=(),
        reports_root=tmp_path,
    )

    with path.open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.reader(
                file
            )
        )

    assert rows == [
        [
            "row",
            "X",
            "Y",
        ],
    ]


def test_save_matrix_csv_rejects_wrong_row_label_count(
    tmp_path,
) -> None:
    with pytest.raises(
        ValueError,
        match="Row-label count",
    ):
        save_matrix_csv(
            section="test_section",
            stem="matrix",
            row_label_name="row",
            row_labels=(
                "A",
            ),
            column_labels=(
                "X",
                "Y",
            ),
            matrix=(
                (1.0, 2.0),
                (3.0, 4.0),
            ),
            reports_root=tmp_path,
        )


def test_save_matrix_csv_rejects_wrong_column_count(
    tmp_path,
) -> None:
    with pytest.raises(
        ValueError,
        match="Matrix must be rectangular",
    ):
        save_matrix_csv(
            section="test_section",
            stem="matrix",
            row_label_name="row",
            row_labels=(
                "A",
                "B",
            ),
            column_labels=(
                "X",
                "Y",
            ),
            matrix=(
                (1.0, 2.0),
                (3.0,),
            ),
            reports_root=tmp_path,
        )


def test_save_matrix_csv_rejects_extra_columns(
    tmp_path,
) -> None:
    with pytest.raises(
        ValueError,
        match="Matrix must be rectangular",
    ):
        save_matrix_csv(
            section="test_section",
            stem="matrix",
            row_label_name="row",
            row_labels=(
                "A",
            ),
            column_labels=(
                "X",
                "Y",
            ),
            matrix=(
                (
                    1.0,
                    2.0,
                    3.0,
                ),
            ),
            reports_root=tmp_path,
        )


def test_save_figure_creates_requested_formats(
    tmp_path,
) -> None:
    fig, ax = plt.subplots()

    ax.plot(
        [0, 1],
        [0, 1],
    )

    paths = save_figure(
        fig=fig,
        section="test_section",
        stem="figure",
        formats=(
            "png",
            "svg",
        ),
        reports_root=tmp_path,
    )

    plt.close(
        fig
    )

    assert len(
        paths
    ) == 2

    assert (
        tmp_path
        / "figures"
        / "test_section"
        / "figure.png"
    ) in paths

    assert (
        tmp_path
        / "figures"
        / "test_section"
        / "figure.svg"
    ) in paths

    for path in paths:
        assert path.exists()

        assert (
            path.stat().st_size
            > 0
        )


def test_save_figure_supports_single_format(
    tmp_path,
) -> None:
    fig, ax = plt.subplots()

    ax.plot(
        [0, 1],
        [1, 0],
    )

    paths = save_figure(
        fig=fig,
        section="test_section",
        stem="figure",
        formats=(
            "png",
        ),
        reports_root=tmp_path,
    )

    plt.close(
        fig
    )

    assert len(
        paths
    ) == 1

    assert (
        paths[0].suffix
        == ".png"
    )


def test_text_report_render(
) -> None:
    report = TextReport()

    report.line(
        "Title"
    )

    report.line()

    report.line(
        "Body"
    )

    assert (
        report.render()
        == "Title\n\nBody\n"
    )


def test_text_report_rule(
) -> None:
    report = TextReport()

    report.rule(
        character="=",
        width=5,
    )

    assert (
        report.render()
        == "=====\n"
    )


def test_text_report_save_without_echo(
    tmp_path,
    capsys,
) -> None:
    report = TextReport()

    report.line(
        "Example report"
    )

    path = report.save(
        section="test_section",
        stem="text_report",
        echo=False,
        reports_root=tmp_path,
    )

    captured = capsys.readouterr()

    assert (
        captured.out
        == ""
    )

    assert path.exists()

    assert (
        path.read_text(
            encoding="utf-8"
        )
        == "Example report\n"
    )


def test_text_report_save_with_echo(
    tmp_path,
    capsys,
) -> None:
    report = TextReport()

    report.line(
        "Example report"
    )

    path = report.save(
        section="test_section",
        stem="text_report",
        echo=True,
        reports_root=tmp_path,
    )

    captured = capsys.readouterr()

    assert (
        captured.out
        == "Example report\n"
    )

    assert path.exists()


def test_reporting_outputs_use_expected_directory_structure(
    tmp_path,
) -> None:
    text_path = save_text_report(
        section="section_a",
        stem="report",
        text="hello",
        reports_root=tmp_path,
    )

    csv_path = save_csv(
        section="section_b",
        stem="table",
        header=(
            "a",
        ),
        rows=(
            (1,),
        ),
        reports_root=tmp_path,
    )

    json_path = save_json(
        section="section_c",
        stem="metadata",
        data={
            "value": 1,
        },
        reports_root=tmp_path,
    )

    assert text_path == (
        tmp_path
        / "text"
        / "section_a"
        / "report.txt"
    )

    assert csv_path == (
        tmp_path
        / "tables"
        / "section_b"
        / "table.csv"
    )

    assert json_path == (
        tmp_path
        / "metadata"
        / "section_c"
        / "metadata.json"
    )