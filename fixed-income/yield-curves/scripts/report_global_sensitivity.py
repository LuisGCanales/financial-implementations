"""Run, compare, and persist global F-TIIE quote-sensitivity diagnostics.

This experiment compares quote-to-curve sensitivity under the same
simultaneous nodal calibration engine for:

    1. LOG_LINEAR_DF
    2. LINEAR_CONTINUOUS_ZERO
    3. CUBIC_CONTINUOUS_ZERO

Each market quote is perturbed symmetrically by +/- BUMP_BP.

The experiment is intentionally separated into:

    src/yield_curves/
        financial logic and structured result objects

    scripts/
        experiment configuration, orchestration, progress logging,
        and persistent analytical outputs

    src/yield_curves/reporting.py
        reusable serialization primitives

    reports/
        persistent analytical artifacts

The expensive global-sensitivity calculation is executed exactly once
per interpolation method. All CSV, TXT, JSON, and figure outputs are
derived from the retained structured result objects without repeating
calibrations.

Persistent outputs
------------------
Tables:
    reports/tables/07_global_sensitivity/
        global_sensitivity_summary.csv
        global_node_sensitivity_long.csv
        global_forward_sensitivity_dense.csv
        global_calibration_diagnostics.csv

        node_zero_sensitivity_matrix_log_linear_df.csv
        node_zero_curvature_matrix_log_linear_df.csv

        node_zero_sensitivity_matrix_linear_continuous_zero.csv
        node_zero_curvature_matrix_linear_continuous_zero.csv

        node_zero_sensitivity_matrix_cubic_continuous_zero.csv
        node_zero_curvature_matrix_cubic_continuous_zero.csv

Figures:
    reports/figures/07_global_sensitivity/
        node_zero_sensitivity_heatmap_log_linear_df.png/.svg
        node_zero_sensitivity_heatmap_linear_continuous_zero.png/.svg
        node_zero_sensitivity_heatmap_cubic_continuous_zero.png/.svg

        off_diagonal_share_by_shock.png/.svg
        forward_sensitivity_rmse_by_shock.png/.svg
        forward_max_abs_sensitivity_by_shock.png/.svg

Text:
    reports/text/07_global_sensitivity/
        global_quote_sensitivity_report.txt

Metadata:
    reports/metadata/07_global_sensitivity/
        experiment_metadata.json
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import matplotlib.pyplot as plt

from yield_curves.calendars import (
    build_projected_mxmc_calendar,
)
from yield_curves.curves import (
    CurveInterpolationMethod,
)
from yield_curves.global_sensitivity import (
    analyze_global_quote_sensitivity,
)
from yield_curves.reporting import (
    TextReport,
    save_csv,
    save_figure,
    save_json,
    save_matrix_csv,
)
from yield_curves.synthetic import (
    read_synthetic_ois_quotes_csv,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

QUOTES_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "ftiie_ois_quotes_v1.csv"
)


REPORT_SECTION = (
    "07_global_sensitivity"
)


SCENARIO_NAME = (
    "FTIIE_KNOWN_TRUTH_V1"
)

CALIBRATION_ENGINE = (
    "simultaneous_nodal_least_squares"
)


BUMP_BP = 1.0

GRID_STEP_DAYS = 7

FORWARD_PERIOD_DAYS = 28


METHODS = (
    CurveInterpolationMethod.LOG_LINEAR_DF,
    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO,
    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO,
)


METHOD_LABELS = {
    CurveInterpolationMethod.LOG_LINEAR_DF:
        "Log-linear DF",

    CurveInterpolationMethod.LINEAR_CONTINUOUS_ZERO:
        "Linear continuous zero",

    CurveInterpolationMethod.CUBIC_CONTINUOUS_ZERO:
        "Cubic continuous zero",
}


def method_slug(
    method: CurveInterpolationMethod,
) -> str:
    """Return a filesystem-friendly interpolation-method label."""

    return (
        method.value.lower()
    )


def project_relative_path(
    path: Path,
) -> str:
    """Return a POSIX path relative to the project root when possible."""

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


def build_progress_callback(
    *,
    method: CurveInterpolationMethod,
    experiment_start: float,
):
    """Build a live progress callback for one interpolation method."""

    method_start = (
        perf_counter()
    )

    def progress(
        message: str,
    ) -> None:
        now = (
            perf_counter()
        )

        method_elapsed = (
            now
            - method_start
        )

        total_elapsed = (
            now
            - experiment_start
        )

        print(
            f"[{method.value}"
            f" | method +{method_elapsed:8.2f}s"
            f" | total +{total_elapsed:8.2f}s] "
            f"{message}",
            flush=True,
        )

    return progress


def append_method_report(
    *,
    text_report: TextReport,
    method: CurveInterpolationMethod,
    sensitivity_report,
) -> None:
    """Append one interpolation-method sensitivity summary."""

    text_report.line(
        METHOD_LABELS[
            method
        ]
    )

    text_report.rule(
        character="-",
        width=150,
    )

    text_report.line(
        f"{'Shock':<10}"
        f"{'Own dZ/dK':>14}"
        f"{'Own Curv':>14}"
        f"{'Max |dZ/dK|':>16}"
        f"{'Max Node':>12}"
        f"{'Off-Diag Share':>17}"
        f"{'Fwd RMSE':>14}"
        f"{'Fwd Max':>14}"
        f"{'Fwd Curv RMSE':>16}"
        f"{'Fwd Curv Max':>16}"
    )

    text_report.line(
        f"{'':<10}"
        f"{'(bp/bp)':>14}"
        f"{'(bp/bp^2)':>14}"
        f"{'(bp/bp)':>16}"
        f"{'':>12}"
        f"{'(%)':>17}"
        f"{'(bp/bp)':>14}"
        f"{'(bp/bp)':>14}"
        f"{'(bp/bp^2)':>16}"
        f"{'(bp/bp^2)':>16}"
    )

    text_report.rule(
        character="-",
        width=150,
    )

    for shock in (
        sensitivity_report.shocks
    ):
        forward = (
            shock.forward_sensitivity
        )

        text_report.line(
            f"{shock.shock_tenor:<10}"
            f"{shock.own_node_sensitivity:>14.6f}"
            f"{shock.own_node_curvature:>14.6f}"
            f"{shock.maximum_abs_node_sensitivity:>16.6f}"
            f"{shock.maximum_abs_node_sensitivity_tenor:>12}"
            f"{100.0 * shock.off_diagonal_share:>17.2f}"
            f"{forward.sensitivity_rmse:>14.6f}"
            f"{forward.maximum_abs_sensitivity:>14.6f}"
            f"{forward.curvature_rmse:>16.6f}"
            f"{forward.maximum_abs_curvature:>16.6f}"
        )

    text_report.line()

    off_diagonal_shares = [
        shock.off_diagonal_share
        for shock
        in sensitivity_report.shocks
    ]

    mean_off_diagonal_share = (
        sum(
            off_diagonal_shares
        )
        / len(
            off_diagonal_shares
        )
    )

    max_off_diagonal_shock = max(
        sensitivity_report.shocks,
        key=lambda shock: (
            shock.off_diagonal_share
        ),
    )

    max_node_shock = max(
        sensitivity_report.shocks,
        key=lambda shock: (
            shock.maximum_abs_node_sensitivity
        ),
    )

    max_forward_shock = max(
        sensitivity_report.shocks,
        key=lambda shock: (
            shock.forward_sensitivity
            .maximum_abs_sensitivity
        ),
    )

    max_forward_curvature_shock = max(
        sensitivity_report.shocks,
        key=lambda shock: (
            shock.forward_sensitivity
            .maximum_abs_curvature
        ),
    )

    text_report.line(
        "Method Summary"
    )

    text_report.line(
        f"  Base calibration success: "
        f"{sensitivity_report.base_calibration.success}"
    )

    text_report.line(
        f"  Base max repricing error (bp): "
        f"{sensitivity_report.base_calibration.max_abs_repricing_error_bp:.8f}"
    )

    text_report.line(
        f"  Base repricing RMSE (bp): "
        f"{sensitivity_report.base_calibration.rmse_repricing_error_bp:.8f}"
    )

    text_report.line(
        f"  Mean off-diagonal share: "
        f"{100.0 * mean_off_diagonal_share:.2f}%"
    )

    text_report.line(
        f"  Maximum off-diagonal share: "
        f"{100.0 * max_off_diagonal_shock.off_diagonal_share:.2f}% "
        f"({max_off_diagonal_shock.shock_tenor})"
    )

    text_report.line(
        f"  Maximum node sensitivity: "
        f"{max_node_shock.maximum_abs_node_sensitivity:.6f} bp/bp "
        f"from {max_node_shock.shock_tenor} shock "
        f"at {max_node_shock.maximum_abs_node_sensitivity_tenor} node"
    )

    text_report.line(
        f"  Maximum dense forward sensitivity: "
        f"{max_forward_shock.forward_sensitivity.maximum_abs_sensitivity:.6f} "
        f"bp/bp from {max_forward_shock.shock_tenor} shock "
        f"at "
        f"{max_forward_shock.forward_sensitivity.maximum_abs_sensitivity_date.isoformat()}"
    )

    text_report.line(
        f"  Maximum dense forward curvature: "
        f"{max_forward_curvature_shock.forward_sensitivity.maximum_abs_curvature:.6f} "
        f"bp/bp^2 from {max_forward_curvature_shock.shock_tenor} shock "
        f"at "
        f"{max_forward_curvature_shock.forward_sensitivity.maximum_abs_curvature_date.isoformat()}"
    )

    text_report.line()


def save_node_sensitivity_heatmap(
    *,
    method: CurveInterpolationMethod,
    sensitivity_report,
) -> tuple[Path, ...]:
    """Persist the quote-to-node zero-sensitivity matrix as a heatmap."""

    row_labels = [
        shock.shock_tenor
        for shock
        in sensitivity_report.shocks
    ]

    column_labels = [
        node.node_tenor
        for node
        in (
            sensitivity_report
            .shocks[0]
            .node_sensitivities
        )
    ]

    matrix = [
        [
            node.central_sensitivity_bp_per_bp
            for node
            in shock.node_sensitivities
        ]
        for shock
        in sensitivity_report.shocks
    ]

    fig, ax = plt.subplots(
        figsize=(
            11.5,
            8.0,
        )
    )

    image = ax.imshow(
        matrix,
        aspect="auto",
    )

    ax.set_title(
        "Quote-to-Node Zero Sensitivity\n"
        f"{METHOD_LABELS[method]}"
    )

    ax.set_xlabel(
        "Calibrated zero-curve node"
    )

    ax.set_ylabel(
        "Shocked market quote"
    )

    ax.set_xticks(
        range(
            len(
                column_labels
            )
        )
    )

    ax.set_xticklabels(
        column_labels,
        rotation=45,
        ha="right",
    )

    ax.set_yticks(
        range(
            len(
                row_labels
            )
        )
    )

    ax.set_yticklabels(
        row_labels
    )

    colorbar = (
        fig.colorbar(
            image,
            ax=ax,
        )
    )

    colorbar.set_label(
        "Central zero sensitivity (bp/bp)"
    )

    fig.tight_layout()

    paths = (
        save_figure(
            fig=fig,
            section=REPORT_SECTION,
            stem=(
                "node_zero_sensitivity_heatmap_"
                f"{method_slug(method)}"
            ),
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


def save_off_diagonal_share_figure(
    *,
    reports,
) -> tuple[Path, ...]:
    """Persist cross-method comparison of nodal sensitivity locality."""

    first_report = (
        reports[
            METHODS[0]
        ]
    )

    tenors = [
        shock.shock_tenor
        for shock
        in first_report.shocks
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
        values = [
            100.0
            * shock.off_diagonal_share
            for shock
            in (
                reports[
                    method
                ].shocks
            )
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
        "Off-Diagonal Quote-to-Node Sensitivity Share"
    )

    ax.set_xlabel(
        "Shocked market quote"
    )

    ax.set_ylabel(
        "Off-diagonal share (%)"
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
            stem=(
                "off_diagonal_share_by_shock"
            ),
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


def save_forward_sensitivity_rmse_figure(
    *,
    reports,
) -> tuple[Path, ...]:
    """Persist cross-method comparison of dense forward sensitivity RMSE."""

    first_report = (
        reports[
            METHODS[0]
        ]
    )

    tenors = [
        shock.shock_tenor
        for shock
        in first_report.shocks
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
        values = [
            shock.forward_sensitivity
            .sensitivity_rmse
            for shock
            in (
                reports[
                    method
                ].shocks
            )
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
        "Dense 28-Day Forward Sensitivity RMSE"
    )

    ax.set_xlabel(
        "Shocked market quote"
    )

    ax.set_ylabel(
        "Forward sensitivity RMSE (bp/bp)"
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
            stem=(
                "forward_sensitivity_rmse_by_shock"
            ),
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


def save_forward_max_sensitivity_figure(
    *,
    reports,
) -> tuple[Path, ...]:
    """Persist cross-method maximum dense forward sensitivity comparison."""

    first_report = (
        reports[
            METHODS[0]
        ]
    )

    tenors = [
        shock.shock_tenor
        for shock
        in first_report.shocks
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
        values = [
            shock.forward_sensitivity
            .maximum_abs_sensitivity
            for shock
            in (
                reports[
                    method
                ].shocks
            )
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
        "Maximum Absolute Dense 28-Day Forward Sensitivity"
    )

    ax.set_xlabel(
        "Shocked market quote"
    )

    ax.set_ylabel(
        "Maximum absolute sensitivity (bp/bp)"
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
            stem=(
                "forward_max_abs_sensitivity_by_shock"
            ),
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
    experiment_start = (
        perf_counter()
    )

    print(
        "Starting F-TIIE global quote-sensitivity comparison.",
        flush=True,
    )

    print(
        f"Methods: "
        f"{', '.join(method.value for method in METHODS)}",
        flush=True,
    )

    print(
        f"Symmetric bump: +/- {BUMP_BP:.4f} bp",
        flush=True,
    )

    print(
        f"Dense forward grid step: "
        f"{GRID_STEP_DAYS} days",
        flush=True,
    )

    print(
        f"Forward period: "
        f"{FORWARD_PERIOD_DAYS} days",
        flush=True,
    )

    print(
        "",
        flush=True,
    )

    quotes = (
        read_synthetic_ois_quotes_csv(
            QUOTES_PATH
        )
    )

    calendar = (
        build_projected_mxmc_calendar(
            start_year=2026,
            end_year=2057,
        )
    )

    # --------------------------------------------------------------
    # Expensive experiment.
    #
    # Each method is analysed exactly once.
    #
    # All persistent outputs below are derived exclusively from these
    # retained report objects.
    # --------------------------------------------------------------

    reports = {}

    method_elapsed_seconds = {}

    reference_date = None

    for method_index, method in enumerate(
        METHODS,
        start=1,
    ):
        method_start = (
            perf_counter()
        )

        total_elapsed = (
            method_start
            - experiment_start
        )

        print(
            "=" * 100,
            flush=True,
        )

        print(
            f"Method {method_index}/{len(METHODS)} "
            f"starting: {method.value} "
            f"| total elapsed={total_elapsed:.2f}s",
            flush=True,
        )

        print(
            "=" * 100,
            flush=True,
        )

        progress = (
            build_progress_callback(
                method=method,
                experiment_start=(
                    experiment_start
                ),
            )
        )

        sensitivity_report = (
            analyze_global_quote_sensitivity(
                quotes=quotes,
                calendar=calendar,
                interpolation_method=method,
                bump_bp=BUMP_BP,
                forward_period_days=(
                    FORWARD_PERIOD_DAYS
                ),
                grid_step_days=(
                    GRID_STEP_DAYS
                ),
                progress_callback=progress,
            )
        )

        elapsed = (
            perf_counter()
            - method_start
        )

        method_elapsed_seconds[
            method
        ] = elapsed

        if reference_date is None:
            reference_date = (
                sensitivity_report
                .reference_date
            )

        elif (
            sensitivity_report
            .reference_date
            != reference_date
        ):
            raise RuntimeError(
                "Interpolation methods produced "
                "different reference dates."
            )

        if not (
            sensitivity_report
            .base_calibration
            .success
        ):
            raise RuntimeError(
                f"Base calibration failed for "
                f"{method.value}: "
                f"{sensitivity_report.base_calibration.message}"
            )

        if (
            sensitivity_report
            .base_calibration
            .max_abs_repricing_error_bp
            > 0.01
        ):
            raise RuntimeError(
                f"Base calibration for "
                f"{method.value} exceeded "
                f"the 0.01 bp repricing tolerance."
            )

        for shock in (
            sensitivity_report.shocks
        ):
            if not (
                shock.plus_calibration_success
                and shock.minus_calibration_success
            ):
                raise RuntimeError(
                    f"Perturbed calibration failed for "
                    f"{method.value}, "
                    f"shock={shock.shock_tenor}."
                )

            if (
                shock.plus_max_abs_repricing_error_bp
                > 0.01
                or
                shock.minus_max_abs_repricing_error_bp
                > 0.01
            ):
                raise RuntimeError(
                    f"Perturbed calibration exceeded "
                    f"0.01 bp repricing tolerance for "
                    f"{method.value}, "
                    f"shock={shock.shock_tenor}."
                )

        reports[
            method
        ] = (
            sensitivity_report
        )

        print(
            f"Method {method.value} complete "
            f"| elapsed={elapsed:.2f}s "
            f"| shocks={len(sensitivity_report.shocks)}",
            flush=True,
        )

        print(
            "",
            flush=True,
        )

    assert reference_date is not None

    calculation_elapsed = (
        perf_counter()
        - experiment_start
    )

    print(
        f"All sensitivity calculations complete "
        f"| elapsed={calculation_elapsed:.2f}s",
        flush=True,
    )

    print(
        "Building persistent report artifacts...",
        flush=True,
    )

    generated_outputs: dict[
        str,
        list[str],
    ] = {}


    # --------------------------------------------------------------
    # Global sensitivity summary.
    #
    # One row per interpolation method and shocked quote.
    # --------------------------------------------------------------

    summary_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "global_sensitivity_summary"
            ),
            header=(
                "scenario",
                "reference_date",
                "method",
                "calibration_engine",
                "bump_bp",
                "shock_index",
                "shock_tenor",
                "own_node_sensitivity_bp_per_bp",
                "own_node_curvature_bp_per_bp2",
                "maximum_abs_node_sensitivity_bp_per_bp",
                "maximum_abs_node_sensitivity_tenor",
                "total_abs_node_sensitivity_bp_per_bp",
                "off_diagonal_abs_sensitivity_bp_per_bp",
                "off_diagonal_share",
                "plus_calibration_success",
                "minus_calibration_success",
                "plus_max_abs_repricing_error_bp",
                "minus_max_abs_repricing_error_bp",
                "forward_observation_count",
                "forward_sensitivity_bias_bp_per_bp",
                "forward_sensitivity_mae_bp_per_bp",
                "forward_sensitivity_rmse_bp_per_bp",
                "forward_max_abs_sensitivity_bp_per_bp",
                "forward_max_abs_sensitivity_date",
                "forward_curvature_rmse_bp_per_bp2",
                "forward_max_abs_curvature_bp_per_bp2",
                "forward_max_abs_curvature_date",
                "grid_step_days",
                "forward_period_days",
            ),
            rows=(
                (
                    SCENARIO_NAME,
                    reference_date.isoformat(),
                    method.value,
                    CALIBRATION_ENGINE,
                    report.bump_bp,
                    shock.shock_index,
                    shock.shock_tenor,
                    shock.own_node_sensitivity,
                    shock.own_node_curvature,
                    shock.maximum_abs_node_sensitivity,
                    shock.maximum_abs_node_sensitivity_tenor,
                    shock.total_abs_node_sensitivity,
                    shock.off_diagonal_abs_sensitivity,
                    shock.off_diagonal_share,
                    shock.plus_calibration_success,
                    shock.minus_calibration_success,
                    shock.plus_max_abs_repricing_error_bp,
                    shock.minus_max_abs_repricing_error_bp,
                    shock.forward_sensitivity.observation_count,
                    shock.forward_sensitivity.sensitivity_bias,
                    shock.forward_sensitivity.sensitivity_mae,
                    shock.forward_sensitivity.sensitivity_rmse,
                    (
                        shock.forward_sensitivity
                        .maximum_abs_sensitivity
                    ),
                    (
                        shock.forward_sensitivity
                        .maximum_abs_sensitivity_date
                        .isoformat()
                    ),
                    shock.forward_sensitivity.curvature_rmse,
                    (
                        shock.forward_sensitivity
                        .maximum_abs_curvature
                    ),
                    (
                        shock.forward_sensitivity
                        .maximum_abs_curvature_date
                        .isoformat()
                    ),
                    report.grid_step_days,
                    report.forward_period_days,
                )
                for method
                in METHODS
                for report
                in (
                    reports[
                        method
                    ],
                )
                for shock
                in report.shocks
            ),
        )
    )

    generated_outputs[
        "summary_tables"
    ] = [
        project_relative_path(
            summary_path
        )
    ]


    # --------------------------------------------------------------
    # Long-form node sensitivity table.
    #
    # This preserves every quote-node sensitivity and curvature value
    # in tidy form for later filtering and analysis.
    # --------------------------------------------------------------

    node_long_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "global_node_sensitivity_long"
            ),
            header=(
                "scenario",
                "reference_date",
                "method",
                "bump_bp",
                "shock_index",
                "shock_tenor",
                "node_index",
                "node_tenor",
                "node_date",
                "maturity_distance",
                "central_sensitivity_bp_per_bp",
                "curvature_bp_per_bp2",
            ),
            rows=(
                (
                    SCENARIO_NAME,
                    reference_date.isoformat(),
                    method.value,
                    report.bump_bp,
                    shock.shock_index,
                    shock.shock_tenor,
                    node.node_index,
                    node.node_tenor,
                    node.node_date.isoformat(),
                    node.maturity_distance,
                    (
                        node
                        .central_sensitivity_bp_per_bp
                    ),
                    (
                        node
                        .curvature_bp_per_bp2
                    ),
                )
                for method
                in METHODS
                for report
                in (
                    reports[
                        method
                    ],
                )
                for shock
                in report.shocks
                for node
                in shock.node_sensitivities
            ),
        )
    )

    generated_outputs[
        "summary_tables"
    ].append(
        project_relative_path(
            node_long_path
        )
    )


    # --------------------------------------------------------------
    # Dense forward sensitivity table.
    #
    # This is especially important to persist because the underlying
    # global recalibration experiment is expensive.
    #
    # Future plots and diagnostics can be constructed directly from
    # this CSV without repeating the +/- quote calibrations.
    # --------------------------------------------------------------

    forward_dense_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "global_forward_sensitivity_dense"
            ),
            header=(
                "scenario",
                "reference_date",
                "method",
                "bump_bp",
                "shock_index",
                "shock_tenor",
                "forward_start_date",
                "forward_end_date",
                "forward_period_days",
                "base_forward_rate",
                "plus_forward_rate",
                "minus_forward_rate",
                "central_sensitivity_bp_per_bp",
                "curvature_bp_per_bp2",
            ),
            rows=(
                (
                    SCENARIO_NAME,
                    reference_date.isoformat(),
                    method.value,
                    report.bump_bp,
                    shock.shock_index,
                    shock.shock_tenor,
                    observation.start_date.isoformat(),
                    observation.end_date.isoformat(),
                    report.forward_period_days,
                    observation.base_forward_rate,
                    observation.plus_forward_rate,
                    observation.minus_forward_rate,
                    (
                        observation
                        .central_sensitivity_bp_per_bp
                    ),
                    (
                        observation
                        .curvature_bp_per_bp2
                    ),
                )
                for method
                in METHODS
                for report
                in (
                    reports[
                        method
                    ],
                )
                for shock
                in report.shocks
                for observation
                in (
                    shock
                    .forward_sensitivity
                    .observations
                )
            ),
        )
    )

    generated_outputs[
        "summary_tables"
    ].append(
        project_relative_path(
            forward_dense_path
        )
    )


    # --------------------------------------------------------------
    # Base-calibration diagnostics.
    # --------------------------------------------------------------

    calibration_path = (
        save_csv(
            section=REPORT_SECTION,
            stem=(
                "global_calibration_diagnostics"
            ),
            header=(
                "scenario",
                "reference_date",
                "method",
                "success",
                "function_evaluations",
                "jacobian_evaluations",
                "cost",
                "optimality",
                "repricing_rmse_bp",
                "max_abs_repricing_error_bp",
                "optimizer_message",
                "global_sensitivity_elapsed_seconds",
            ),
            rows=(
                (
                    SCENARIO_NAME,
                    reference_date.isoformat(),
                    method.value,
                    calibration.success,
                    calibration.function_evaluations,
                    (
                        ""
                        if (
                            calibration
                            .jacobian_evaluations
                            is None
                        )
                        else (
                            calibration
                            .jacobian_evaluations
                        )
                    ),
                    calibration.cost,
                    calibration.optimality,
                    calibration.rmse_repricing_error_bp,
                    calibration.max_abs_repricing_error_bp,
                    calibration.message,
                    method_elapsed_seconds[
                        method
                    ],
                )
                for method
                in METHODS
                for calibration
                in (
                    reports[
                        method
                    ].base_calibration,
                )
            ),
        )
    )

    generated_outputs[
        "summary_tables"
    ].append(
        project_relative_path(
            calibration_path
        )
    )


    # --------------------------------------------------------------
    # Explicit quote-node matrices.
    #
    # Rows:
    #     shocked market quotes
    #
    # Columns:
    #     calibrated zero-curve nodes
    #
    # Values:
    #     sensitivity or curvature
    # --------------------------------------------------------------

    generated_outputs[
        "matrix_tables"
    ] = []

    for method in METHODS:
        report = (
            reports[
                method
            ]
        )

        row_labels = [
            shock.shock_tenor
            for shock
            in report.shocks
        ]

        column_labels = [
            node.node_tenor
            for node
            in (
                report
                .shocks[0]
                .node_sensitivities
            )
        ]

        sensitivity_matrix = [
            [
                node.central_sensitivity_bp_per_bp
                for node
                in shock.node_sensitivities
            ]
            for shock
            in report.shocks
        ]

        curvature_matrix = [
            [
                node.curvature_bp_per_bp2
                for node
                in shock.node_sensitivities
            ]
            for shock
            in report.shocks
        ]

        sensitivity_matrix_path = (
            save_matrix_csv(
                section=REPORT_SECTION,
                stem=(
                    "node_zero_sensitivity_matrix_"
                    f"{method_slug(method)}"
                ),
                row_label_name=(
                    "shock_tenor"
                ),
                row_labels=(
                    row_labels
                ),
                column_labels=(
                    column_labels
                ),
                matrix=(
                    sensitivity_matrix
                ),
            )
        )

        curvature_matrix_path = (
            save_matrix_csv(
                section=REPORT_SECTION,
                stem=(
                    "node_zero_curvature_matrix_"
                    f"{method_slug(method)}"
                ),
                row_label_name=(
                    "shock_tenor"
                ),
                row_labels=(
                    row_labels
                ),
                column_labels=(
                    column_labels
                ),
                matrix=(
                    curvature_matrix
                ),
            )
        )

        generated_outputs[
            "matrix_tables"
        ].extend(
            (
                project_relative_path(
                    sensitivity_matrix_path
                ),
                project_relative_path(
                    curvature_matrix_path
                ),
            )
        )


    # --------------------------------------------------------------
    # Figures.
    # --------------------------------------------------------------

    generated_outputs[
        "figures"
    ] = []

    for method in METHODS:
        figure_paths = (
            save_node_sensitivity_heatmap(
                method=method,
                sensitivity_report=(
                    reports[
                        method
                    ]
                ),
            )
        )

        generated_outputs[
            "figures"
        ].extend(
            project_relative_path(
                path
            )
            for path
            in figure_paths
        )

    off_diagonal_paths = (
        save_off_diagonal_share_figure(
            reports=reports
        )
    )

    generated_outputs[
        "figures"
    ].extend(
        project_relative_path(
            path
        )
        for path
        in off_diagonal_paths
    )

    forward_rmse_paths = (
        save_forward_sensitivity_rmse_figure(
            reports=reports
        )
    )

    generated_outputs[
        "figures"
    ].extend(
        project_relative_path(
            path
        )
        for path
        in forward_rmse_paths
    )

    forward_max_paths = (
        save_forward_max_sensitivity_figure(
            reports=reports
        )
    )

    generated_outputs[
        "figures"
    ].extend(
        project_relative_path(
            path
        )
        for path
        in forward_max_paths
    )


    # --------------------------------------------------------------
    # Human-readable text report.
    # --------------------------------------------------------------

    text_report = (
        TextReport()
    )

    text_report.line(
        "F-TIIE Global Quote Sensitivity Comparison"
    )

    text_report.rule(
        character="=",
        width=150,
    )

    text_report.line()

    text_report.line(
        f"Scenario: "
        f"{SCENARIO_NAME}"
    )

    text_report.line(
        f"Reference date: "
        f"{reference_date.isoformat()}"
    )

    text_report.line(
        f"Calibration engine: "
        f"{CALIBRATION_ENGINE}"
    )

    text_report.line(
        f"Symmetric quote bump: "
        f"+/- {BUMP_BP:.4f} bp"
    )

    text_report.line(
        f"Forward period: "
        f"{FORWARD_PERIOD_DAYS} days"
    )

    text_report.line(
        f"Dense forward grid: "
        f"{GRID_STEP_DAYS} days"
    )

    text_report.line()

    text_report.line(
        "Matrix convention:"
    )

    text_report.line(
        "  rows    = shocked market quotes"
    )

    text_report.line(
        "  columns = calibrated zero-curve nodes"
    )

    text_report.line(
        "  sensitivity values = "
        "central dZ_node / dK_quote in bp/bp"
    )

    text_report.line(
        "  curvature values   = "
        "central second-order zero response in bp/bp^2"
    )

    text_report.line()

    text_report.line(
        "Method runtimes:"
    )

    for method in METHODS:
        text_report.line(
            f"  {method.value}: "
            f"{method_elapsed_seconds[method]:.2f} s"
        )

    text_report.line()

    for method in METHODS:
        append_method_report(
            text_report=(
                text_report
            ),
            method=method,
            sensitivity_report=(
                reports[
                    method
                ]
            ),
        )

    text_path = (
        text_report.save(
            section=REPORT_SECTION,
            stem=(
                "global_quote_sensitivity_report"
            ),
            echo=True,
        )
    )

    generated_outputs[
        "text"
    ] = [
        project_relative_path(
            text_path
        )
    ]


    # --------------------------------------------------------------
    # Experiment metadata.
    #
    # Large numerical arrays are deliberately excluded from JSON.
    # Their canonical machine-readable representation is the CSV
    # output written above.
    # --------------------------------------------------------------

    pre_metadata_elapsed = (
        perf_counter()
        - experiment_start
    )

    metadata_path = (
        save_json(
            section=REPORT_SECTION,
            stem=(
                "experiment_metadata"
            ),
            data={
                "scenario": (
                    SCENARIO_NAME
                ),
                "reference_date": (
                    reference_date
                    .isoformat()
                ),
                "quote_source": (
                    project_relative_path(
                        QUOTES_PATH
                    )
                ),
                "quote_count": (
                    len(
                        quotes
                    )
                ),
                "calibration_engine": (
                    CALIBRATION_ENGINE
                ),
                "interpolation_methods": [
                    method.value
                    for method
                    in METHODS
                ],
                "shock_design": {
                    "type": (
                        "symmetric_one_factor_at_a_time"
                    ),
                    "bump_bp": (
                        BUMP_BP
                    ),
                    "shocks_per_method": (
                        len(
                            quotes
                        )
                    ),
                    "perturbed_calibrations_per_method": (
                        2
                        * len(
                            quotes
                        )
                    ),
                    "base_calibrations_per_method": 1,
                },
                "forward_analysis": {
                    "forward_period_days": (
                        FORWARD_PERIOD_DAYS
                    ),
                    "grid_step_days": (
                        GRID_STEP_DAYS
                    ),
                },
                "matrix_definition": {
                    "rows": (
                        "shocked market quotes"
                    ),
                    "columns": (
                        "calibrated zero-curve nodes"
                    ),
                    "sensitivity_values": (
                        "central zero sensitivity "
                        "in bp/bp"
                    ),
                    "curvature_values": (
                        "central second-order zero "
                        "response in bp/bp^2"
                    ),
                },
                "locality_metric": {
                    "name": (
                        "off_diagonal_share"
                    ),
                    "definition": (
                        "sum(abs(J_ji), j != i) / "
                        "sum(abs(J_ji), all j)"
                    ),
                },
                "dense_forward_output_reason": (
                    "Persisted because symmetric quote "
                    "perturbation requires repeated global "
                    "calibrations. The stored dense series "
                    "supports subsequent forward-response "
                    "analysis and visualization without "
                    "recalibration."
                ),
                "runtime_seconds": {
                    method.value: (
                        method_elapsed_seconds[
                            method
                        ]
                    )
                    for method
                    in METHODS
                },
                "calculation_and_reporting_elapsed_seconds_before_metadata": (
                    pre_metadata_elapsed
                ),
                "outputs": (
                    generated_outputs
                ),
            },
        )
    )

    total_elapsed = (
        perf_counter()
        - experiment_start
    )

    print(
        "",
        flush=True,
    )

    print(
        "=" * 100,
        flush=True,
    )

    print(
        "Global sensitivity reporting complete.",
        flush=True,
    )

    print(
        f"Total elapsed: "
        f"{total_elapsed:.2f}s",
        flush=True,
    )

    print(
        f"Metadata: "
        f"{project_relative_path(metadata_path)}",
        flush=True,
    )

    print(
        "=" * 100,
        flush=True,
    )


if __name__ == "__main__":
    main()