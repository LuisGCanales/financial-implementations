"""Plot persisted global forward-sensitivity propagation heatmaps.

This script performs NO calibration.

It consumes the persistent outputs produced by:

    scripts/report_global_sensitivity.py

Specifically:

    reports/tables/07_global_sensitivity/
        global_forward_sensitivity_dense.csv
        global_node_sensitivity_long.csv

The objective is to visualize where a shock to each market quote
propagates across the dense 28-day forward curve.

Two color-scale regimes are produced.

1. Common robust scale
----------------------
A symmetric, zero-centered scale shared across all interpolation
methods.

The absolute color limit is defined by a pooled quantile of the
absolute forward sensitivities across all methods.

Default:

    pooled |dF/dK| 99.5th percentile

This deliberately clips a small fraction of extreme observations so
that the broader propagation structure remains visible while preserving
cross-method comparability.

2. Common full scale
--------------------
A symmetric, zero-centered scale shared across all methods using the
largest absolute forward sensitivity observed anywhere in the complete
experiment.

This preserves the full magnitude information but may visually compress
smaller sensitivities.

Persistent outputs
------------------
Figures:

    reports/figures/07_global_sensitivity/
        forward_sensitivity_heatmap_<method>_robust_common_scale.png/.svg
        forward_sensitivity_heatmap_<method>_full_common_scale.png/.svg

Tables:

    reports/tables/07_global_sensitivity/
        forward_sensitivity_heatmap_scale_diagnostics.csv

Metadata:

    reports/metadata/07_global_sensitivity/
        forward_sensitivity_heatmap_metadata.json
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from yield_curves.reporting import (
    save_csv,
    save_figure,
    save_json,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
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


ROBUST_QUANTILE = 0.995


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


def method_slug(
    method: str,
) -> str:
    """Return filesystem-friendly method label."""

    return (
        method.lower()
    )


def project_relative_path(
    path: Path,
) -> str:
    """Return project-relative POSIX path when possible."""

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


def act_360(
    reference_date: date,
    target_date: date,
) -> float:
    """Return ACT/360 time from reference date."""

    return (
        target_date
        - reference_date
    ).days / 360.0


def read_dense_forward_sensitivity():
    """Read and reshape persisted dense forward sensitivities.

    Returns
    -------
    reference_date
        Common curve reference date.

    scenario
        Experiment scenario name.

    data
        Dictionary indexed by interpolation method.

        Each method contains:

            shock_indices
            shock_labels
            forward_dates
            forward_years
            matrix

        Matrix convention:

            rows    = shocked market quotes
            columns = dense forward-start dates
            values  = central dF/dK in bp/bp
    """

    if not FORWARD_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing persisted forward sensitivity data: "
            f"{FORWARD_DATA_PATH}"
        )

    with FORWARD_DATA_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(
                file
            )
        )

    if not rows:
        raise ValueError(
            "Dense forward-sensitivity CSV is empty."
        )

    reference_dates = {
        row[
            "reference_date"
        ]
        for row in rows
    }

    if len(
        reference_dates
    ) != 1:
        raise ValueError(
            "Expected exactly one reference date."
        )

    scenarios = {
        row[
            "scenario"
        ]
        for row in rows
    }

    if len(
        scenarios
    ) != 1:
        raise ValueError(
            "Expected exactly one scenario."
        )

    reference_date = (
        date.fromisoformat(
            next(
                iter(
                    reference_dates
                )
            )
        )
    )

    scenario = (
        next(
            iter(
                scenarios
            )
        )
    )

    data = {}

    for method in METHODS:
        method_rows = [
            row
            for row
            in rows
            if (
                row[
                    "method"
                ]
                == method
            )
        ]

        if not method_rows:
            raise ValueError(
                f"No persisted observations for "
                f"{method}."
            )

        shock_pairs = sorted(
            {
                (
                    int(
                        row[
                            "shock_index"
                        ]
                    ),
                    row[
                        "shock_tenor"
                    ],
                )
                for row
                in method_rows
            },
            key=lambda item: (
                item[0]
            ),
        )

        shock_indices = tuple(
            item[0]
            for item
            in shock_pairs
        )

        shock_labels = tuple(
            item[1]
            for item
            in shock_pairs
        )

        forward_dates = tuple(
            sorted(
                {
                    date.fromisoformat(
                        row[
                            "forward_start_date"
                        ]
                    )
                    for row
                    in method_rows
                }
            )
        )

        date_to_column = {
            forward_date: column_index
            for column_index, forward_date
            in enumerate(
                forward_dates
            )
        }

        shock_to_row = {
            shock_index: row_index
            for row_index, shock_index
            in enumerate(
                shock_indices
            )
        }

        matrix = np.full(
            (
                len(
                    shock_indices
                ),
                len(
                    forward_dates
                ),
            ),
            np.nan,
            dtype=float,
        )

        for row in method_rows:
            shock_index = int(
                row[
                    "shock_index"
                ]
            )

            forward_date = (
                date.fromisoformat(
                    row[
                        "forward_start_date"
                    ]
                )
            )

            sensitivity = float(
                row[
                    "central_sensitivity_bp_per_bp"
                ]
            )

            matrix[
                shock_to_row[
                    shock_index
                ],
                date_to_column[
                    forward_date
                ],
            ] = sensitivity

        if np.isnan(
            matrix
        ).any():
            raise ValueError(
                f"Incomplete forward-sensitivity matrix "
                f"for {method}."
            )

        forward_years = np.asarray(
            [
                act_360(
                    reference_date,
                    forward_date,
                )
                for forward_date
                in forward_dates
            ],
            dtype=float,
        )

        data[
            method
        ] = {
            "shock_indices":
                shock_indices,

            "shock_labels":
                shock_labels,

            "forward_dates":
                forward_dates,

            "forward_years":
                forward_years,

            "matrix":
                matrix,
        }

    return (
        reference_date,
        scenario,
        data,
    )


def read_pillar_years(
    *,
    reference_date: date,
) -> dict[int, float]:
    """Read actual calibrated pillar dates for shock-reference markers.

    The node-sensitivity table contains the exact calibrated node dates.

    For each shock index, the diagonal node is used:

        shock_index == node_index

    Node dates are required to agree across interpolation methods.
    """

    if not NODE_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing persisted node sensitivity data: "
            f"{NODE_DATA_PATH}"
        )

    with NODE_DATA_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(
                file
            )
        )

    dates_by_index: dict[
        int,
        set[date],
    ] = {}

    for row in rows:
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

        node_date = (
            date.fromisoformat(
                row[
                    "node_date"
                ]
            )
        )

        dates_by_index.setdefault(
            shock_index,
            set(),
        ).add(
            node_date
        )

    pillar_years = {}

    for shock_index, node_dates in (
        dates_by_index.items()
    ):
        if len(
            node_dates
        ) != 1:
            raise ValueError(
                f"Node date for shock index "
                f"{shock_index} differs across methods."
            )

        node_date = next(
            iter(
                node_dates
            )
        )

        pillar_years[
            shock_index
        ] = (
            act_360(
                reference_date,
                node_date,
            )
        )

    return pillar_years


def calculate_scale_diagnostics(
    *,
    data,
):
    """Calculate full and robust common color-scale limits."""

    pooled_values = np.concatenate(
        [
            data[
                method
            ][
                "matrix"
            ].ravel()
            for method
            in METHODS
        ]
    )

    pooled_absolute = np.abs(
        pooled_values
    )

    full_cap = float(
        np.max(
            pooled_absolute
        )
    )

    robust_cap = float(
        np.quantile(
            pooled_absolute,
            ROBUST_QUANTILE,
        )
    )

    if robust_cap <= 0.0:
        raise ValueError(
            "Robust heatmap scale must be positive."
        )

    diagnostics = []

    for method in METHODS:
        matrix = (
            data[
                method
            ][
                "matrix"
            ]
        )

        absolute = np.abs(
            matrix.ravel()
        )

        diagnostics.append(
            {
                "scope":
                    "method",

                "method":
                    method,

                "observation_count":
                    int(
                        absolute.size
                    ),

                "abs_max_bp_per_bp":
                    float(
                        np.max(
                            absolute
                        )
                    ),

                "abs_q95_bp_per_bp":
                    float(
                        np.quantile(
                            absolute,
                            0.95,
                        )
                    ),

                "abs_q99_bp_per_bp":
                    float(
                        np.quantile(
                            absolute,
                            0.99,
                        )
                    ),

                "abs_q995_bp_per_bp":
                    float(
                        np.quantile(
                            absolute,
                            0.995,
                        )
                    ),

                "abs_q999_bp_per_bp":
                    float(
                        np.quantile(
                            absolute,
                            0.999,
                        )
                    ),

                "common_robust_cap_bp_per_bp":
                    robust_cap,

                "common_full_cap_bp_per_bp":
                    full_cap,

                "fraction_clipped_at_robust_cap":
                    float(
                        np.mean(
                            absolute
                            > robust_cap
                        )
                    ),
            }
        )

    diagnostics.append(
        {
            "scope":
                "pooled",

            "method":
                "ALL_METHODS",

            "observation_count":
                int(
                    pooled_absolute.size
                ),

            "abs_max_bp_per_bp":
                full_cap,

            "abs_q95_bp_per_bp":
                float(
                    np.quantile(
                        pooled_absolute,
                        0.95,
                    )
                ),

            "abs_q99_bp_per_bp":
                float(
                    np.quantile(
                        pooled_absolute,
                        0.99,
                    )
                ),

            "abs_q995_bp_per_bp":
                robust_cap,

            "abs_q999_bp_per_bp":
                float(
                    np.quantile(
                        pooled_absolute,
                        0.999,
                    )
                ),

            "common_robust_cap_bp_per_bp":
                robust_cap,

            "common_full_cap_bp_per_bp":
                full_cap,

            "fraction_clipped_at_robust_cap":
                float(
                    np.mean(
                        pooled_absolute
                        > robust_cap
                    )
                ),
        }
    )

    return (
        robust_cap,
        full_cap,
        diagnostics,
    )


def save_forward_heatmap(
    *,
    method: str,
    method_data,
    pillar_years: dict[int, float],
    color_cap: float,
    scale_name: str,
    scale_description: str,
) -> tuple[Path, ...]:
    """Persist one signed dense-forward sensitivity heatmap."""

    matrix = (
        method_data[
            "matrix"
        ]
    )

    shock_indices = (
        method_data[
            "shock_indices"
        ]
    )

    shock_labels = (
        method_data[
            "shock_labels"
        ]
    )

    forward_years = (
        method_data[
            "forward_years"
        ]
    )

    clipped_fraction = float(
        np.mean(
            np.abs(
                matrix
            )
            > color_cap
        )
    )

    norm = TwoSlopeNorm(
        vmin=-color_cap,
        vcenter=0.0,
        vmax=color_cap,
    )

    fig, ax = plt.subplots(
        figsize=(
            13.0,
            7.5,
        )
    )

    image = ax.imshow(
        matrix,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
        extent=(
            float(
                forward_years[0]
            ),
            float(
                forward_years[-1]
            ),
            len(
                shock_labels
            )
            - 0.5,
            -0.5,
        ),
        cmap="RdBu_r",
        norm=norm,
    )

    ax.set_title(
        "Dense 28-Day Forward Sensitivity Propagation\n"
        f"{METHOD_LABELS[method]} | "
        f"{scale_description}"
    )

    ax.set_xlabel(
        "Forward start time from reference date "
        "(ACT/360 years)"
    )

    ax.set_ylabel(
        "Shocked market quote"
    )

    ax.set_yticks(
        np.arange(
            len(
                shock_labels
            )
        )
    )

    ax.set_yticklabels(
        shock_labels
    )

    # Mark the calibrated maturity associated with each shocked quote.
    #
    # These markers indicate where the corresponding shocked market
    # instrument sits on the forward-maturity axis.
    for row_index, shock_index in enumerate(
        shock_indices
    ):
        pillar_year = (
            pillar_years.get(
                shock_index
            )
        )

        if pillar_year is None:
            continue

        ax.plot(
            pillar_year,
            row_index,
            marker="|",
            markersize=12,
            markeredgewidth=1.5,
        )

    colorbar = fig.colorbar(
        image,
        ax=ax,
        extend=(
            "both"
            if (
                clipped_fraction
                > 0.0
            )
            else "neither"
        ),
    )

    colorbar.set_label(
        "Central forward sensitivity "
        "dF / dK (bp/bp)"
    )

    ax.text(
        0.99,
        0.01,
        (
            f"color limit = +/- {color_cap:.4f} bp/bp"
            f" | clipped cells = "
            f"{100.0 * clipped_fraction:.3f}%"
        ),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
    )

    fig.tight_layout()

    paths = save_figure(
        fig=fig,
        section=REPORT_SECTION,
        stem=(
            "forward_sensitivity_heatmap_"
            f"{method_slug(method)}_"
            f"{scale_name}"
        ),
        formats=(
            "png",
            "svg",
        ),
    )

    plt.close(
        fig
    )

    return paths


def main() -> None:
    (
        reference_date,
        scenario,
        data,
    ) = (
        read_dense_forward_sensitivity()
    )

    pillar_years = (
        read_pillar_years(
            reference_date=(
                reference_date
            ),
        )
    )

    (
        robust_cap,
        full_cap,
        diagnostics,
    ) = (
        calculate_scale_diagnostics(
            data=data
        )
    )

    print(
        "Forward-sensitivity heatmap scale diagnostics"
    )

    print(
        f"Scenario: {scenario}"
    )

    print(
        f"Reference date: "
        f"{reference_date.isoformat()}"
    )

    print(
        f"Pooled full absolute maximum: "
        f"{full_cap:.6f} bp/bp"
    )

    print(
        f"Pooled "
        f"{100.0 * ROBUST_QUANTILE:.2f}th "
        f"absolute percentile: "
        f"{robust_cap:.6f} bp/bp"
    )

    print()

    diagnostics_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "forward_sensitivity_heatmap_"
                "scale_diagnostics"
            ),
            header=(
                "scope",
                "method",
                "observation_count",
                "abs_max_bp_per_bp",
                "abs_q95_bp_per_bp",
                "abs_q99_bp_per_bp",
                "abs_q995_bp_per_bp",
                "abs_q999_bp_per_bp",
                "common_robust_cap_bp_per_bp",
                "common_full_cap_bp_per_bp",
                "fraction_clipped_at_robust_cap",
            ),
            rows=(
                (
                    item[
                        "scope"
                    ],
                    item[
                        "method"
                    ],
                    item[
                        "observation_count"
                    ],
                    item[
                        "abs_max_bp_per_bp"
                    ],
                    item[
                        "abs_q95_bp_per_bp"
                    ],
                    item[
                        "abs_q99_bp_per_bp"
                    ],
                    item[
                        "abs_q995_bp_per_bp"
                    ],
                    item[
                        "abs_q999_bp_per_bp"
                    ],
                    item[
                        "common_robust_cap_bp_per_bp"
                    ],
                    item[
                        "common_full_cap_bp_per_bp"
                    ],
                    item[
                        "fraction_clipped_at_robust_cap"
                    ],
                )
                for item
                in diagnostics
            ),
        )
    )

    figure_outputs = []

    # --------------------------------------------------------------
    # Primary diagnostic:
    #
    # common robust scale.
    #
    # This is the most useful view for studying propagation structure
    # while retaining cross-method comparability.
    # --------------------------------------------------------------

    for method in METHODS:
        paths = (
            save_forward_heatmap(
                method=method,
                method_data=(
                    data[
                        method
                    ]
                ),
                pillar_years=(
                    pillar_years
                ),
                color_cap=(
                    robust_cap
                ),
                scale_name=(
                    "robust_common_scale"
                ),
                scale_description=(
                    f"common pooled "
                    f"{100.0 * ROBUST_QUANTILE:.1f}th "
                    f"percentile scale"
                ),
            )
        )

        figure_outputs.extend(
            project_relative_path(
                path
            )
            for path
            in paths
        )

    # --------------------------------------------------------------
    # Audit/reference view:
    #
    # common full scale.
    #
    # This preserves every observed magnitude without clipping.
    # --------------------------------------------------------------

    for method in METHODS:
        paths = (
            save_forward_heatmap(
                method=method,
                method_data=(
                    data[
                        method
                    ]
                ),
                pillar_years=(
                    pillar_years
                ),
                color_cap=(
                    full_cap
                ),
                scale_name=(
                    "full_common_scale"
                ),
                scale_description=(
                    "common full-range scale"
                ),
            )
        )

        figure_outputs.extend(
            project_relative_path(
                path
            )
            for path
            in paths
        )

    metadata_path = (
        save_json(
            section=REPORT_SECTION,
            stem=(
                "forward_sensitivity_"
                "heatmap_metadata"
            ),
            data={
                "scenario": (
                    scenario
                ),
                "reference_date": (
                    reference_date
                    .isoformat()
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
                "matrix_definition": {
                    "rows": (
                        "shocked market quotes"
                    ),
                    "columns": (
                        "dense 28-day forward start dates"
                    ),
                    "values": (
                        "central forward sensitivity "
                        "dF/dK in bp/bp"
                    ),
                },
                "color_scale": {
                    "center": 0.0,
                    "diverging": True,
                    "robust_quantile": (
                        ROBUST_QUANTILE
                    ),
                    "robust_common_cap_bp_per_bp": (
                        robust_cap
                    ),
                    "full_common_cap_bp_per_bp": (
                        full_cap
                    ),
                    "robust_scale_interpretation": (
                        "Common symmetric scale across all "
                        "methods using the pooled absolute "
                        "sensitivity quantile. Values outside "
                        "the cap are intentionally saturated."
                    ),
                    "full_scale_interpretation": (
                        "Common symmetric scale across all "
                        "methods using the largest absolute "
                        "observed sensitivity. No values are "
                        "intentionally clipped."
                    ),
                },
                "scale_diagnostics_output": (
                    project_relative_path(
                        diagnostics_path
                    )
                ),
                "figure_outputs": (
                    figure_outputs
                ),
            },
        )
    )

    print(
        f"Scale diagnostics saved to: "
        f"{project_relative_path(diagnostics_path)}"
    )

    print(
        f"Heatmap metadata saved to: "
        f"{project_relative_path(metadata_path)}"
    )

    print(
        f"Generated figure files: "
        f"{len(figure_outputs)}"
    )


if __name__ == "__main__":
    main()