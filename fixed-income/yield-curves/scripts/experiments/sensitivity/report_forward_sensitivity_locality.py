"""Calculate and persist forward-sensitivity locality diagnostics.

This script performs NO curve calibration.

It consumes the persisted global-sensitivity experiment:

    reports/tables/07_global_sensitivity/
        global_forward_sensitivity_dense.csv
        global_node_sensitivity_long.csv

and derives absolute-sensitivity-weighted locality metrics for every
interpolation-method / shocked-quote combination.

Primary metric
--------------
RMS distance from shocked maturity:

    L_i = sqrt(
        sum_j w_ij * (t_j - T_i)^2
    )

where:

    w_ij
    =
    |dF_j/dK_i|
    /
    sum_k |dF_k/dK_i|

Smaller values indicate a more maturity-localized forward response.

Persistent outputs
------------------
Tables:
    reports/tables/07_global_sensitivity/
        forward_sensitivity_locality.csv

Figures:
    reports/figures/07_global_sensitivity/
        forward_sensitivity_rms_locality_by_shock.png/.svg
        forward_sensitivity_spread_by_shock.png/.svg
        forward_sensitivity_center_offset_by_shock.png/.svg
        forward_sensitivity_mass_within_2y_by_shock.png/.svg

Text:
    reports/text/07_global_sensitivity/
        forward_sensitivity_locality_report.txt

Metadata:
    reports/metadata/07_global_sensitivity/
        forward_sensitivity_locality_metadata.json
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt

from yield_curves.project_paths import find_project_root
from yield_curves.global_sensitivity import (
    calculate_forward_sensitivity_locality,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
    save_figure,
    save_json,
)


PROJECT_ROOT = (
    find_project_root(Path(__file__))
)

REPORT_SECTION = (
    "07_global_sensitivity"
)


FORWARD_DATA_PATH = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / REPORT_SECTION
    / "global_forward_sensitivity_dense.csv"
)

NODE_DATA_PATH = (
    PROJECT_ROOT
    / "reports"
    / "tables"
    / REPORT_SECTION
    / "global_node_sensitivity_long.csv"
)


METHODS = (
    "LOG_LINEAR_DF",
    "LINEAR_CONTINUOUS_ZERO",
    "CUBIC_CONTINUOUS_ZERO",
)


METHOD_LABELS = {
    "LOG_LINEAR_DF":
        "Log-linear DF",

    "LINEAR_CONTINUOUS_ZERO":
        "Linear continuous zero",

    "CUBIC_CONTINUOUS_ZERO":
        "Cubic continuous zero",
}


def project_relative_path(
    path: Path,
) -> str:
    try:
        return (
            path
            .relative_to(
                PROJECT_ROOT
            )
            .as_posix()
        )

    except ValueError:
        return (
            path.as_posix()
        )


def read_csv_rows(
    path: Path,
) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            path
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        return list(
            csv.DictReader(
                file
            )
        )


def load_locality_results():
    forward_rows = (
        read_csv_rows(
            FORWARD_DATA_PATH
        )
    )

    node_rows = (
        read_csv_rows(
            NODE_DATA_PATH
        )
    )

    if not forward_rows:
        raise ValueError(
            "Forward sensitivity CSV is empty."
        )

    reference_date = (
        date.fromisoformat(
            forward_rows[0][
                "reference_date"
            ]
        )
    )

    scenario = (
        forward_rows[0][
            "scenario"
        ]
    )

    diagonal_node_dates = {}

    for row in node_rows:
        shock_index = int(
            row[
                "shock_index"
            ]
        )

        node_index = int(
            row[
                "node_index"
            ]
        )

        if (
            shock_index
            != node_index
        ):
            continue

        key = (
            row[
                "method"
            ],
            shock_index,
            row[
                "shock_tenor"
            ],
        )

        diagonal_node_dates[
            key
        ] = (
            date.fromisoformat(
                row[
                    "node_date"
                ]
            )
        )

    grouped = defaultdict(
        list
    )

    for row in forward_rows:
        key = (
            row[
                "method"
            ],
            int(
                row[
                    "shock_index"
                ]
            ),
            row[
                "shock_tenor"
            ],
        )

        grouped[
            key
        ].append(
            row
        )

    results = []

    for (
        method,
        shock_index,
        shock_tenor,
    ), rows in grouped.items():
        rows = sorted(
            rows,
            key=lambda row: (
                row[
                    "forward_start_date"
                ]
            ),
        )

        shock_pillar_date = (
            diagonal_node_dates[
                (
                    method,
                    shock_index,
                    shock_tenor,
                )
            ]
        )

        locality = (
            calculate_forward_sensitivity_locality(
                reference_date=(
                    reference_date
                ),
                shock_pillar_date=(
                    shock_pillar_date
                ),
                forward_start_dates=tuple(
                    date.fromisoformat(
                        row[
                            "forward_start_date"
                        ]
                    )
                    for row
                    in rows
                ),
                sensitivities_bp_per_bp=tuple(
                    float(
                        row[
                            "central_sensitivity_bp_per_bp"
                        ]
                    )
                    for row
                    in rows
                ),
            )
        )

        results.append(
            {
                "scenario":
                    scenario,

                "reference_date":
                    reference_date,

                "method":
                    method,

                "shock_index":
                    shock_index,

                "shock_tenor":
                    shock_tenor,

                "shock_pillar_date":
                    shock_pillar_date,

                "locality":
                    locality,
            }
        )

    results.sort(
        key=lambda item: (
            METHODS.index(
                item[
                    "method"
                ]
            ),
            item[
                "shock_index"
            ],
        )
    )

    return (
        scenario,
        reference_date,
        results,
    )


def plot_metric(
    *,
    results,
    attribute: str,
    title: str,
    ylabel: str,
    stem: str,
    multiplier: float = 1.0,
) -> tuple[Path, ...]:
    first_method = [
        item
        for item
        in results
        if (
            item[
                "method"
            ]
            == METHODS[0]
        )
    ]

    tenors = [
        item[
            "shock_tenor"
        ]
        for item
        in first_method
    ]

    x = list(
        range(
            len(
                tenors
            )
        )
    )

    fig, ax = plt.subplots(
        figsize=(
            11.0,
            5.8,
        )
    )

    for method in METHODS:
        method_results = [
            item
            for item
            in results
            if (
                item[
                    "method"
                ]
                == method
            )
        ]

        values = [
            multiplier
            * getattr(
                item[
                    "locality"
                ],
                attribute,
            )
            for item
            in method_results
        ]

        ax.plot(
            x,
            values,
            marker="o",
            linewidth=1.6,
            label=(
                METHOD_LABELS[
                    method
                ]
            ),
        )

    ax.set_title(
        title
    )

    ax.set_xlabel(
        "Shocked market quote"
    )

    ax.set_ylabel(
        ylabel
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(
        tenors,
        rotation=45,
        ha="right",
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    fig.tight_layout()

    paths = (
        save_figure(
            fig=fig,
            section=REPORT_SECTION,
            stem=stem,
            formats=(
                "png",
                "svg",
            ),
        )
    )

    plt.close(
        fig
    )

    return paths


def main() -> None:
    (
        scenario,
        reference_date,
        results,
    ) = (
        load_locality_results()
    )

    table_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "forward_sensitivity_locality"
            ),
            header=(
                "scenario",
                "reference_date",
                "method",
                "shock_index",
                "shock_tenor",
                "shock_pillar_date",
                "shock_pillar_years",
                "weighted_center_years",
                "center_offset_from_shock_years",
                "weighted_spread_years",
                "rms_distance_from_shock_years",
                "sensitivity_mass_within_1y",
                "sensitivity_mass_within_2y",
                "observation_count",
            ),
            rows=(
                (
                    item[
                        "scenario"
                    ],
                    item[
                        "reference_date"
                    ].isoformat(),
                    item[
                        "method"
                    ],
                    item[
                        "shock_index"
                    ],
                    item[
                        "shock_tenor"
                    ],
                    item[
                        "shock_pillar_date"
                    ].isoformat(),
                    item[
                        "locality"
                    ].shock_pillar_years,
                    item[
                        "locality"
                    ].weighted_center_years,
                    item[
                        "locality"
                    ].center_offset_from_shock_years,
                    item[
                        "locality"
                    ].weighted_spread_years,
                    item[
                        "locality"
                    ].rms_distance_from_shock_years,
                    item[
                        "locality"
                    ].sensitivity_mass_within_1y,
                    item[
                        "locality"
                    ].sensitivity_mass_within_2y,
                    item[
                        "locality"
                    ].observation_count,
                )
                for item
                in results
            ),
        )
    )

    figure_paths = []

    figure_paths.extend(
        plot_metric(
            results=results,
            attribute=(
                "rms_distance_from_shock_years"
            ),
            title=(
                "Forward Sensitivity Locality "
                "— RMS Distance from Shock"
            ),
            ylabel=(
                "RMS distance (ACT/360 years)"
            ),
            stem=(
                "forward_sensitivity_"
                "rms_locality_by_shock"
            ),
        )
    )

    figure_paths.extend(
        plot_metric(
            results=results,
            attribute=(
                "weighted_spread_years"
            ),
            title=(
                "Forward Sensitivity "
                "Weighted Spread"
            ),
            ylabel=(
                "Weighted spread "
                "(ACT/360 years)"
            ),
            stem=(
                "forward_sensitivity_"
                "spread_by_shock"
            ),
        )
    )

    figure_paths.extend(
        plot_metric(
            results=results,
            attribute=(
                "center_offset_from_shock_years"
            ),
            title=(
                "Forward Sensitivity Center "
                "Offset from Shock Maturity"
            ),
            ylabel=(
                "Center offset "
                "(ACT/360 years)"
            ),
            stem=(
                "forward_sensitivity_"
                "center_offset_by_shock"
            ),
        )
    )

    figure_paths.extend(
        plot_metric(
            results=results,
            attribute=(
                "sensitivity_mass_within_2y"
            ),
            title=(
                "Forward Sensitivity Mass "
                "Within +/- 2Y of Shock"
            ),
            ylabel=(
                "Sensitivity mass (%)"
            ),
            stem=(
                "forward_sensitivity_"
                "mass_within_2y_by_shock"
            ),
            multiplier=100.0,
        )
    )

    text_report = (
        TextReport()
    )

    text_report.line(
        "F-TIIE Forward Sensitivity Locality"
    )

    text_report.rule(
        character="=",
        width=110,
    )

    text_report.line()

    text_report.line(
        f"Scenario: {scenario}"
    )

    text_report.line(
        f"Reference date: "
        f"{reference_date.isoformat()}"
    )

    text_report.line()

    text_report.line(
        f"{'Method':<28}"
        f"{'Mean RMS Dist':>16}"
        f"{'Max RMS Dist':>16}"
        f"{'Max Shock':>12}"
        f"{'Mean Spread':>16}"
        f"{'Mean +/-2Y Mass':>18}"
    )

    text_report.rule(
        character="-",
        width=110,
    )

    for method in METHODS:
        method_results = [
            item
            for item
            in results
            if (
                item[
                    "method"
                ]
                == method
            )
        ]

        rms_values = [
            item[
                "locality"
            ].rms_distance_from_shock_years
            for item
            in method_results
        ]

        spread_values = [
            item[
                "locality"
            ].weighted_spread_years
            for item
            in method_results
        ]

        mass_values = [
            item[
                "locality"
            ].sensitivity_mass_within_2y
            for item
            in method_results
        ]

        max_item = max(
            method_results,
            key=lambda item: (
                item[
                    "locality"
                ]
                .rms_distance_from_shock_years
            ),
        )

        text_report.line(
            f"{METHOD_LABELS[method]:<28}"
            f"{sum(rms_values) / len(rms_values):>16.4f}"
            f"{max(rms_values):>16.4f}"
            f"{max_item['shock_tenor']:>12}"
            f"{sum(spread_values) / len(spread_values):>16.4f}"
            f"{100.0 * sum(mass_values) / len(mass_values):>17.2f}%"
        )

    text_path = (
        text_report.save(
            section=REPORT_SECTION,
            stem=(
                "forward_sensitivity_"
                "locality_report"
            ),
            echo=True,
        )
    )

    metadata_path = (
        save_json(
            section=REPORT_SECTION,
            stem=(
                "forward_sensitivity_"
                "locality_metadata"
            ),
            data={
                "scenario": (
                    scenario
                ),
                "reference_date": (
                    reference_date.isoformat()
                ),
                "source_forward_data": (
                    project_relative_path(
                        FORWARD_DATA_PATH
                    )
                ),
                "source_node_data": (
                    project_relative_path(
                        NODE_DATA_PATH
                    )
                ),
                "primary_metric": {
                    "name": (
                        "rms_distance_from_shock_years"
                    ),
                    "definition": (
                        "sqrt(sum_j w_j "
                        "* (t_j - T_shock)^2)"
                    ),
                    "weights": (
                        "absolute central forward "
                        "sensitivity normalized to sum to one"
                    ),
                },
                "companion_metrics": (
                    "weighted_center_years, "
                    "center_offset_from_shock_years, "
                    "weighted_spread_years, "
                    "sensitivity_mass_within_1y, "
                    "sensitivity_mass_within_2y"
                ),
                "outputs": {
                    "table": (
                        project_relative_path(
                            table_path
                        )
                    ),
                    "text": (
                        project_relative_path(
                            text_path
                        )
                    ),
                    "figures": [
                        project_relative_path(
                            path
                        )
                        for path
                        in figure_paths
                    ],
                },
            },
        )
    )

    print(
        f"Locality table: "
        f"{project_relative_path(table_path)}"
    )

    print(
        f"Locality metadata: "
        f"{project_relative_path(metadata_path)}"
    )


if __name__ == "__main__":
    main()