# Test coverage map

This is a contract navigation map based on the C05a **collection** at revision
`666a38bd8078a482dcb9182e8c07b9c53dab4a7b` (2026-11-06). Representative source
names below locate contracts; they are not an exhaustive assertion dump or a new
test execution report. Source/tests are authoritative for exact expressions.

## Counts and evidence meanings

| Layer | Test source modules | Test function definitions | Collected cases | Selected non-slow | Selected slow |
|---|---:|---:|---:|---:|---:|
| Architecture | 1 | 10 | 10 | 10 | 0 |
| Calibration | 5 | 64 | 182 | 182 | 0 |
| Research | 9 | 98 | 147 | 120 | 27 |
| Tooling | 6 | 47 | 146 | 146 | 0 |
| Unit | 17 | 195 | 550 | 550 | 0 |
| **Total** | **38** | **414** | **1035** | **1008** | **27** |

A source function is a `test_` definition before parametrization. A collected
case is a pytest node ID after parameter expansion. Marker selection chooses
cases (`1008 + 27 = 1035`); `not slow` is not a timing guarantee. Actual execution
runs selected cases and produces outcomes. Code coverage requires separate
instrumentation of executed source lines/branches; these counts establish
neither executed passes nor line/branch coverage percentages. C05b runs only the
published small public example, not this suite. See [testing](testing.md) for
commands, environment/plot dependencies, marker rules and C06 release checks.

## Fixtures and reading the map

Each row identifies a test module, contract, representative tests/parameter
groups, fixture assumptions, numerical or rejection condition, marker selection
and authority. Repeated modules split distinct subcontracts; module counts must
not be summed across those repeated rows. Counts in the module column are
`functions / cases` for that whole module, before any subcontract split.
All modules except the two sensitivity modules are entirely non-slow. No shared
expensive sweep fixture should be reached by a non-slow consumer.

Frozen fixtures refer to the synthetic
[`ftiie_ois_quotes_v1.csv`](../data/synthetic/ftiie_ois_quotes_v1.csv), the
[`baseline reference`](../tests/fixtures/ftiie_baseline_reference_v1.json), and
[`mxmc_2026.csv`](../data/calendars/mxmc_2026.csv), as applicable.
Projected long calendars are research models, not verified future official data.
Temporary files/CLI output roots belong to pytest fixtures. Small pricing/curve
contracts often use analytical flat curves or explicit nodes, not market quotes.

## Financial conventions

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_conventions.py](../tests/unit/test_conventions.py) (9 / 174) | Closed Core-v1 field values/types; ACT/360 day count. `test_every_noncanonical_field_is_rejected`; `test_direct_callers_validate_profile`. | Every dataclass field; altered values/types, nonfinite numbers and direct primitive callers. | Reject every noncanonical profile; actual days / 360; reversed dates raise. | Non-slow | [Contract](conventions.md) |

## Calendars and coverage

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_calendars.py](../tests/unit/test_calendars.py) (8 / 8) | Weekend/holiday exclusions and signed business-day arithmetic. `test_add_negative_business_days`; `test_zero_business_day_offset_does_not_adjust`. | Small injected holiday sets and weekend-only calendars. | Exact dates; zero offset does not adjust. | Non-slow | [Contract](input_contract.md) |
| [tests/unit/test_mxmc_calendar.py](../tests/unit/test_mxmc_calendar.py) (10 / 17) | Frozen 2026 facts, T+2 and raw-byte provenance. `test_t_plus_two_skips_independence_day`; `test_checksum_tracks_file_bytes_even_when_calendar_values_match`. | data/calendars/mxmc_2026.csv; temporary CSV variants, invalid/missing files. | Exact holiday/date/hash equality; malformed CSV and missing file raise. | Non-slow | [Contract](conventions.md) |
| [tests/research/test_projected_mxmc_calendar.py](../tests/research/test_projected_mxmc_calendar.py) (5 / 5) | Projected holiday model equals frozen 2026 set and provides declared long coverage. `test_projected_2026_matches_verified_2026_holidays`; `test_projected_calendar_covers_long_horizon`. | Projected 2026 / 2026–2057 calendar and frozen 2026 CSV. | Exact set/known dates; no authentication of future official holidays. | Non-slow | [Contract](assumptions_limitations.md) |
| [tests/unit/test_general_inputs.py](../tests/unit/test_general_inputs.py) (21 / 47) | CSV shape/units/provenance; H01 identity; inclusive date coverage and baseline preflight. `test_invalid_csv_reports_schema_or_row_context`; `test_coverage_check_includes_payment_lag_after_contractual_maturity`; `test_same_calendar_name_does_not_imply_same_financial_identity`. | Temporary CSV/BOM/optional columns; 17 malformed CSV cases; 7 date-operation cases; short covered quotes. | Rates remain decimal; classification conflicts reject; uncovered payments raise; only outer tenor whitespace canonicalizes. | Non-slow | [Contract](input_contract.md) |

## Schedules and observations

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_schedules.py](../tests/unit/test_schedules.py) (7 / 7) | T+2, 28D periods, contiguous adjusted boundaries, payment lag and final stub. `test_holiday_adjustment_preserves_contiguous_periods`; `test_final_stub_is_supported_explicitly`. | Small calendars with explicit holiday shifts; exact-period and stub maturities. | Exact dates/accruals; maturity must follow effective date. | Non-slow | [Contract](conventions.md) |
| [tests/unit/test_observations.py](../tests/unit/test_observations.py) (7 / 7) | Overnight weights cover coupon and realized compounding uses calendar days. `test_weekend_is_carried_by_friday_fixing`; `test_constant_rate_compounding`; `test_missing_fixing_fails_explicitly`. | Weekend, holiday and mixed periods; frozen MXMC 2026; constant realized fixings. | Friday weight 3/360; holiday weight 2/360; missing fixing and nonbusiness start reject. See T01. | Non-slow | [Contract](conventions.md) |
| [tests/unit/test_tenors.py](../tests/unit/test_tenors.py) (10 / 10) | Calendar-month/year tenor arithmetic is separate from schedule adjustments. `test_month_end_is_clipped`; `test_leap_day_plus_one_year`. | Month/year strings, invalid/zero tenors, month-end/leap dates and synthetic maturities. | Exact clipped dates; invalid/zero tenor raises. | Non-slow | [Contract](conventions.md) |
| [tests/unit/test_date_grid_contracts.py](../tests/unit/test_date_grid_contracts.py) (20 / 73) | Inclusive grids versus regular complete-forward grids; guard/evaluation order and signed internal time. `test_forward_grid_requires_complete_period`; `test_diagnostics_keeps_lazy_rate_evaluation_before_date_overflow`; `test_locality_accepts_numpy_sensitivities_without_changing_return_types`. | Off-step terminal dates, period/step combinations, date limits, analytical/numpy locality inputs. | Append terminal only for inclusive contract; reject invalid period/step/horizon in specified order; public domain stays bounded. | Non-slow | [Contract](architecture.md) |

## Instrument and pricing

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_instruments.py](../tests/unit/test_instruments.py) (12 / 14) | Aligned coupons/legs and complete observations; zero spread; positive position notional. `test_floating_observations_cover_each_coupon`; `test_builder_rejects_spread_before_calendar_access`; `test_calendar_family_does_not_restrict_instance_name`. | Frozen MXMC 2026 fixture; short OIS, explicit spread and notional guards. | Notional <= 0 rejects; nonzero spread rejects before calendar access; family is separate from instance name. | Non-slow | [Contract](conventions.md) |
| [tests/unit/test_pricing.py](../tests/unit/test_pricing.py) (8 / 11) | DF-ratio projection, par zero NPV, separate curve parameters and position-notional scaling. `test_projected_coupon_telescopes_to_curve_ratio`; `test_projection_and_discount_curves_are_separable`; `test_downstream_notional_scales_pv_without_changing_profile`. | Short OIS with 1,000,000 notional; frozen calendar; flat analytical projection/discount curves. | Product telescopes to DF ratio; par NPV approximately zero; par rate independent of notional; spread rejects. | Non-slow | [Contract](integration_contract.md) |
| [tests/unit/test_shared_quote_repricing.py](../tests/unit/test_shared_quote_repricing.py) (12 / 28) | Neutral quote identity, independent reconstruction, bp sign/order and exact status boundaries. `test_four_paths_rebuild_identical_contracts`; `test_repricing_ignores_stored_calibration_quotes`; `test_forged_successful_solver_checks_cannot_make_bad_curve_pass`. | Shared two-quote sequential/baseline fixture and weekend-only covered calendar; forged checks; boundary errors. | PASS/REVIEW/FAIL from absolute bp errors; nonfinite guards; downstream notional leaves calibration unit contract unchanged. | Non-slow | [Contract](validation.md) |

## Curve interpolation

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_curves.py](../tests/unit/test_curves.py) (9 / 13) | Flat analytical curve, minimal DF protocol, enum and factory mapping. `test_nodal_factory_preserves_representations`; `test_discount_factor_curve_minimal_protocol`. | Flat and small nodal curves; all four methods; unknown method. | DF(origin)=1; analytical DF/zero/forward identities; unknown method and early dates raise. | Non-slow | [Contract](interpolation.md) |
| [tests/unit/test_log_linear_curve.py](../tests/unit/test_log_linear_curve.py) (7 / 7) | Log-DF segment interpolation and constant segment forward. `test_interpolation_is_linear_in_log_df`; `test_curve_rejects_non_positive_df`. | Small explicit nodal dates/DFs. | Exact nodes; log-linear identity; nonpositive DF, unsorted dates and extrapolation reject. | Non-slow | [Contract](interpolation.md) |
| [tests/unit/test_linear_zero_curve.py](../tests/unit/test_linear_zero_curve.py) (6 / 6) | Linear continuous-zero interpolation and first-zero origin convention. `test_first_segment_uses_first_node_zero_rate`; `test_constant_node_zeros_produce_flat_zero_curve`. | Explicit nodal factors and constant nodal zero examples. | Origin DF=1; linear zero interpolation; terminal extrapolation rejects. | Non-slow | [Contract](interpolation.md) |
| [tests/unit/test_cubic_zero_curve.py](../tests/unit/test_cubic_zero_curve.py) (7 / 17) | Natural cubic origin anchor and instantaneous forward math. `test_natural_cubic_zero_anchor_and_forward_math`; `test_cubic_constructor_rejects_invalid_nodes_or_discount_factors`. | Explicit knots, malformed nodes and invalid date intervals. | f=z+t*z'; nodal DF reproduction; forward continuity; invalid nodes/factors/range reject. | Non-slow | [Contract](interpolation.md) |
| [tests/unit/test_pchip_zero_curve.py](../tests/unit/test_pchip_zero_curve.py) (11 / 11) | Experimental PCHIP representation and monotone-zero example. `test_pchip_zero_curve_does_not_overshoot_monotone_nodes`; `test_pchip_curve_forward_rate_matches_discount_factor_identity`. | Small monotone/flat node sets, inadequate node count and invalid DFs. | DF/zero/origin/forward identities; finite instantaneous forwards; >=2 nodes, positive factors and supported dates required. | Non-slow | [Contract](interpolation.md) |

## Sequential bootstrap

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/calibration/test_bootstrap.py](../tests/calibration/test_bootstrap.py) (10 / 16) | One positive node per ordered final-payment pillar; scalar convergence and final-curve fit. `test_calibrated_instruments_reprice_from_final_curve`; `test_sequential_rejects_invalid_objective_or_root_without_retry`; `test_sequential_root_diagnostics_distinguish_endpoint_and_brent`. | Frozen 15-quote synthetic CSV/projected 2026–2057 calendar; mocked objective/root/Brent cases. | abs(error_bp) <= 0.01; OUT_OF_CURVE_RANGE; invalid objective/root raises without retry; endpoint/Brent diagnostics differ. | Non-slow | [Contract](methodology.md) |
| [tests/calibration/test_interpolation_methods.py](../tests/calibration/test_interpolation_methods.py) (9 / 13) | Local methods preserve wrapper/type/pillars; capabilities are exhaustive/immutable. `test_capabilities_cover_every_known_method_explicitly`; `test_sequential_rejects_before_preparation_or_solve`. | Frozen quotes/calendar; enum methods and unknown/unsupported combinations. | abs(error_bp) <= 0.01; cubic/PCHIP sequential rejection precedes preparation and solve. | Non-slow | [Contract](extending.md) |

## Simultaneous calibration

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/calibration/test_simultaneous_calibration.py](../tests/calibration/test_simultaneous_calibration.py) (9 / 27) | Warm starts, local-method agreement, cubic fit, log-DF objective and solver defaults. `test_all_methods_preserve_warm_start_contract`; `test_invalid_explicit_initial_vector_rejects_without_fallback`; `test_simultaneous_objective_and_solver_defaults_are_explicit`. | Frozen quotes/projected calendar; short quote slices; eight method/start and eight invalid-vector cases; mocked least_squares. | Fit <= 0.01 bp; local sequential DF comparison abs=1e-9; invalid vector has no fallback; solver defaults are separate below. | Non-slow | [Contract](methodology.md) |

## Baseline input and acceptance

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/calibration/test_baseline.py](../tests/calibration/test_baseline.py) (7 / 7) | Frozen numerical regression; current cubic simultaneous policy; fixed keyword-only public API. `test_baseline_matches_pre_separation_reference`; `test_solver_failure_is_distinct_from_acceptance`; `test_public_in_memory_consumer_needs_only_provider_contract`. | One shared frozen 15-quote baseline/projected calendar; tests/fixtures/ftiie_baseline_reference_v1.json; isolated public-consumer process. | Regression tolerances below, with rel=0; success alone is insufficient; absent curve rejects. | Non-slow | [Contract](integration_contract.md) |
| [tests/calibration/test_baseline_acceptance.py](../tests/calibration/test_baseline_acceptance.py) (29 / 119) | Preflight and H01 reject malformed inputs before financial work. `test_bad_inputs_never_reach_solver`; `test_assessment_rejects_bad_inputs_without_repricing`; `test_h01_invalid_tenors_reject_before_solver_or_repricing`. | 17 bad-input cases for both build/assessment; five invalid tenor cases; small shared accepted result. | Build raises BaselineInputError; assessment records issues; solver/repricing no-call guards. | Non-slow | [Contract](validation.md) |
| [tests/calibration/test_baseline_acceptance.py](../tests/calibration/test_baseline_acceptance.py) (29 / 119) | Curve geometry, solver declarations, nonfinite/empty checks and pricing errors. `test_corrupt_structure_is_rejected_before_pricing`; `test_valid_structure_still_requires_checks_and_no_issues`; `test_pricing_domain_error_becomes_rejection`. | Seven structure corruptions; nonempty-check and domain-failure injections. | Reject wrong class/reference/pillars/counts/DFs; skipped/failed repricing has infinite max, not zero fit. | Non-slow | [Contract](validation.md) |
| [tests/calibration/test_baseline_acceptance.py](../tests/calibration/test_baseline_acceptance.py) (29 / 119) | Standard versus custom policy and tolerance boundaries. `test_standalone_identity_depends_on_explicit_path`; `test_standard_threshold_boundaries_preserve_baseline_acceptance`. | Omitted versus explicit tolerances (six cases); six threshold-boundary cases. | Any explicit override is custom; standard PASS 0.01 / FAIL 0.10 bp; REVIEW rejects baseline use; invalid configuration raises. | Non-slow | [Contract](snapshots.md) |

## Live financial bindings

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/calibration/test_baseline_acceptance.py](../tests/calibration/test_baseline_acceptance.py) (29 / 119) | Copied inputs/policy and exact live payload binding, including mutable spline/solver state. `test_build_freezes_external_inputs_before_solver`; `test_mutable_spline_state_invalidates_live_result`; `test_mutating_calibration_after_build_invalidates_live_result`; `test_live_acceptance_query_does_no_financial_work`. | Small accepted result; external quote/calendar mutation; three spline and twelve calibration mutations; no-call sentinels. | Historical acceptance plus unchanged binding required; comparison is exact value identity, not repricing tolerance; query does no financial work. | Non-slow | [Contract](integration_contract.md) |

## Snapshot publication and assurance

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/unit/test_snapshots.py](../tests/unit/test_snapshots.py) (31 / 100) | Execution provenance capture and standard publication authority. `test_provenance_and_inputs_are_captured_before_build`; `test_execution_mixing_rejected_before_writes`; `test_custom_pass_cannot_publish`. | Shared two-quote projected-2026 execution; temporary source/output files; 13 mixed-bound-value and two custom-pass cases. | Reject mixed context/provenance/payload or custom authority before writes; envelope is workflow-issued. | Non-slow | [Contract](snapshots.md) |
| [tests/unit/test_snapshots.py](../tests/unit/test_snapshots.py) (31 / 100) | Accepted promotion, rejected archives and atomic reader boundary. `test_publish_accepted_and_preserve_previous_runs`; `test_rejected_run_is_archived_without_replacing_current`; `test_reader_observes_old_complete_run_until_atomic_commit`; `test_commit_failure_semantics`. | Temporary roots; accepted/rejected results; injected writes/rename/replace/fsync failures (six commit cases). | Rejected never replaces pointer; replacement is commit point; post-replacement fsync can raise with new run current. Reader interleaving is not T02 process-race evidence. | Non-slow | [Contract](snapshots.md) |
| [tests/unit/test_snapshots.py](../tests/unit/test_snapshots.py) (31 / 100) | Resolver integrity/schema/inventory and legacy exclusion. `test_current_reader_rejects_invalid_pointer_manifest_or_metadata_without_fallback`; `test_legacy_and_unknown_schemas_are_not_promoted_or_migrated`; `test_flat_legacy_is_never_current`. | 16 pointer/manifest/metadata corruptions; legacy/unknown schema variants; frozen legacy paths. | Missing/invalid pointer, hashes/inventory or unsupported schema rejects without fallback/migration. | Non-slow | [Contract](snapshots.md) |
| [tests/unit/test_snapshots.py](../tests/unit/test_snapshots.py) (31 / 100) | Financial assurance resists internally inconsistent rehashed archives and does no solve/write. `test_assurance_rejects_incoherence_with_rehashed_files`; `test_assurance_rejects_unsupported_historical_policy_after_outer_integrity_passes`; `test_assurance_reprices_without_solver_or_any_write`. | 17 incoherence variants; three unsupported policy variants; reconstructed curve and no-call/write sentinels. | Outer checksum validity is insufficient; context/payload/history/repricing must match supported V1; solver history is not re-executed. | Non-slow | [Contract](snapshots.md) |
| [tests/unit/test_snapshots.py](../tests/unit/test_snapshots.py) (31 / 100) | Operational/assurance CLI integration, required inputs, explicit demo and coverage. `test_operational_and_assurance_cli_integration`; `test_cli_requires_every_input`; `test_cli_insufficient_calendar_does_not_publish`; `test_explicit_demo_uses_synthetic_inputs`. | Temporary input/output roots and subprocess CLIs; seven omitted flags; explicit synthetic demo destination. | Exit status and publication state checked; insufficient coverage fails before publication; demo fit < 1e-5 bp is fixture-specific. | Non-slow | [Contract](cli.md) |

## Dependency boundaries

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/architecture/test_dependencies.py](../tests/architecture/test_dependencies.py) (10 / 10) | Transitive layer constraints, no core financial I/O, script imports and assurance call restrictions. `test_package_layers_are_explicit_and_imports_point_inward`; `test_financial_context_policy_has_no_filesystem_or_adapter_dependencies`; `test_snapshot_assurance_has_no_solver_or_publication_calls`. | AST/import graph of src and scripts; fresh interpreter import checks; explicit historical method tuples. | Forbidden transitive imports/calls reject; calibration type imports do not imply a solver call. | Non-slow | [Contract](architecture.md) |

## Research recovery and sensitivity

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/research/test_curve_diagnostics.py](../tests/research/test_curve_diagnostics.py) (6 / 6) | Exact segment/jump math and sampled flat-curve stability. `test_identical_segment_slopes_produce_zero_jump`; `test_flat_curve_sampled_forward_is_stable`. | Small explicit log-linear and analytical flat curves. | Zero jump abs=1e-10; flat forward standard deviation abs=1e-12; method-specific report only for log-linear. | Non-slow | [Contract](methodology.md) |
| [tests/research/test_curve_validation.py](../tests/research/test_curve_validation.py) (9 / 9) | Historical sequential VALID/REVIEW/INVALID differs from baseline acceptance. `test_repricing_threshold_review`; `test_critical_issue_changes_curve_to_invalid`. | Frozen synthetic quotes/projected calendar and one sequential build; injected warnings/critical issue. | Shared repricing thresholds; warnings lead REVIEW, critical issues INVALID. | Non-slow | [Contract](validation.md) |
| [tests/research/test_recovery.py](../tests/research/test_recovery.py) (4 / 4) | Known-truth recovery errors, relative DF ppm and reference-date guards. `test_identical_curves_have_zero_recovery_error`; `test_reference_dates_must_match`. | Analytical equal/perturbed curves and mismatched reference dates. | Zero versus nonzero error; incompatible reference dates raise. | Non-slow | [Contract](methodology.md) |
| [tests/research/test_horizon_recovery.py](../tests/research/test_horizon_recovery.py) (6 / 6) | Contiguous horizons, boundary ownership and terminal inclusion. `test_boundary_date_belongs_to_later_bucket`; `test_final_horizon_includes_last_curve_date`. | Named maturity horizons and equal/perturbed analytical curves. | Boundary belongs to later bucket; final endpoint included; equal curves have zero error. | Non-slow | [Contract](methodology.md) |
| [tests/research/test_synthetic_curve.py](../tests/research/test_synthetic_curve.py) (4 / 4) | Scenario origin and shape are known-truth assumptions. `test_reference_discount_factor_is_one`; `test_synthetic_curve_is_non_flat`. | FTIIE_KNOWN_TRUTH_V1 smooth synthetic curve and sampled dates. | Scenario-specific positive/decreasing DFs/rate ranges are not universal acceptance requirements. | Non-slow | [Contract](assumptions_limitations.md) |
| [tests/research/test_synthetic_quotes.py](../tests/research/test_synthetic_quotes.py) (9 / 9) | Synthetic tenor/classification identity and generating-model par quotes. `test_each_synthetic_quote_reprices_to_zero`; `test_mismatched_curve_reference_date_is_rejected`. | Generated canonical synthetic tenors, projected calendar and known truth. | Par NPV approximately zero; common effective/reference date; incompatible truth reference rejects. | Non-slow | [Contract](assumptions_limitations.md) |
| [tests/research/test_quote_sensitivity.py](../tests/research/test_quote_sensitivity.py) (24 / 73) | Sequential one-sided/central shocks, upstream invariance and neutral-bump input guards. `test_upstream_df_changes_are_numerically_negligible`; `test_central_upstream_curvature_is_zero`; `test_neutral_bump_bad_index`. | Frozen 15-quote report/central_report fixtures; short bounded inputs for neutral-engine contracts. | Finite responses/curvature, unchanged upstream nodes and invalid-index/nonfinite-bump rejection; 17 slow consumers listed below. | 56 non-slow / 17 slow | [Contract](evidence/risk.md) |
| [tests/research/test_global_sensitivity.py](../tests/research/test_global_sensitivity.py) (31 / 31) | Simultaneous central shocks, dimensions/diagonal/aggregate metrics, forward response and locality. `test_calculate_forward_sensitivity_exact_linear_response`; `test_global_own_node_metrics_match_diagonal`; `test_global_forward_locality_metrics_are_valid`. | Analytical helper curves and shared cubic_global_report over frozen 15 quotes; short neutral-input case. | Exact analytical central response; fit/finite/locality contracts; invalid period/grid/bump/empty inputs reject; 10 slow consumers below. | 21 non-slow / 10 slow | [Contract](evidence/risk.md) |

## Reporting and CLI tooling

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/tooling/test_reporting.py](../tests/tooling/test_reporting.py) (22 / 22) | CSV/JSON/text/matrix/figure serialization and explicit output destinations. `test_save_matrix_csv_rejects_wrong_column_count`; `test_explicit_destination_does_not_discover_checkout`. | tmp_path, small matrices/text and temporary Matplotlib plots. | Content/directory/format equality; invalid dimensions raise; explicit destination bypasses checkout discovery. | Non-slow | [Contract](architecture.md) |
| [tests/tooling/test_project_paths.py](../tests/tooling/test_project_paths.py) (2 / 2) | Locate checkout markers from file or directory; reject paths outside project. `test_find_project_root_accepts_file_and_directory_paths`; `test_find_project_root_fails_without_project_markers`. | Checkout marker files and temporary directory. | Exact root path or FileNotFoundError. | Non-slow | [Contract](architecture.md) |
| [tests/tooling/test_experiment_reports_root.py](../tests/tooling/test_experiment_reports_root.py) (10 / 32) | Explicit root propagation across saved-data producer/consumers/metadata. `test_missing_explicit_inputs_never_fall_back_to_checkout`; `test_metadata_preserves_historical_relative_path_presentation`. | Imported script helpers, temporary relocated evidence and mocked expensive producers. | Missing explicit data fails without fallback; output paths/numbers and historical relative presentation preserved. | Non-slow | [Contract](evidence/reproduce.md) |
| [tests/tooling/test_research_paths.py](../tests/tooling/test_research_paths.py) (1 / 2) | Saved sensitivity readers accept relocated evidence. `test_sensitivity_readers_open_relocated_evidence`. | Two parametrized CSV consumer readers and temporary evidence root. | Read supplied root, with no historical-output dependency. | Non-slow | [Contract](evidence/reproduce.md) |
| [tests/tooling/test_presentation_date_helpers.py](../tests/tooling/test_presentation_date_helpers.py) (5 / 73) | Presentation date-grid and signed ACT/360 contracts. `test_grid_endpoints_types_and_order`; `test_presentation_act360_remains_signed`. | Imported plotting/report helpers, date/step/guard and signed-offset parameter groups. | Inclusive/regular endpoint/type/order and exact offset/360.0; guard order/date limits retained. | Non-slow | [Contract](architecture.md) |

## Numerical reference maintenance

| Test module (functions / cases) | Contract and representative tests | Inputs / fixture assumptions | Tolerance or rejection condition | Selection | Authority |
|---|---|---|---|---|---|
| [tests/tooling/test_reference_candidates.py](../tests/tooling/test_reference_candidates.py) (7 / 15) | Exclusive candidate outputs and human-owned frozen reference workflow. `test_cli_rejects_unsafe_destination_before_financial_work`; `test_exclusive_creation_handles_race`; `test_capture_deterministic_public_api_and_v1_shape`; `test_rejected_capture_has_no_candidate`. | Temporary candidate destinations; frozen/aliased/missing canonical paths; mocked race; small public build, no full reference generation. | Unsafe/existing/frozen destinations reject before financial work; exclusive race rejects; rejected build emits no candidate. | Non-slow | [Contract](../scripts/tests/README.md) |

## Numerical meanings

These thresholds have distinct purposes and units; `1e-9` is not a universal
financial accuracy requirement.

| Purpose | Precise source expression / meaning | Source |
|---|---|---|
| Frozen regression DF, zero, model rate | `pytest.approx(node["discount_factor"], abs=1e-9, rel=0)`, `pytest.approx(node["zero_rate"], abs=1e-9, rel=0)`, `pytest.approx(saved["model_quote"], abs=1e-9, rel=0)` | [test_baseline.py](../tests/calibration/test_baseline.py), `test_baseline_matches_pre_separation_reference` |
| Frozen regression bp errors/aggregate | `pytest.approx(saved["error_bp"], abs=1e-5, rel=0)`; aggregate uses `pytest.approx(expected["max_abs_repricing_error_bp"], abs=1e-5, rel=0)` | Same regression test; error fields are already bp. |
| Frozen regression forward rates | `pytest.approx(saved["forward_rate"], abs=1e-8, rel=0)` | Same regression test; rates remain decimal. |
| Standard baseline PASS | `absolute_error_bp <= pass_tolerance_bp`, default `0.01` bp | [repricing.py](../src/yield_curves/repricing.py), [baseline.py](../src/yield_curves/baseline.py) |
| Standard REVIEW / FAIL | Finite absolute error `> 0.01` and `<= 0.10` is REVIEW; `> 0.10` or nonfinite is FAIL. REVIEW rejects baseline use. | [validation](validation.md); shared classifier boundary tests and six baseline-boundary cases. |
| Simultaneous termination | `ftol=1e-13`, `xtol=1e-13`, `gtol=1e-13`, `max_nfev=5_000`; log-DF bounds from `lower_df_bound=1e-6`, `upper_df_bound=2.0` | [calibration.py](../src/yield_curves/calibration.py), objective/default test in [test_simultaneous_calibration.py](../tests/calibration/test_simultaneous_calibration.py) |
| Sequential Brent termination | `xtol=1e-14`, `rtol=1e-12`, `maxiter=200` | [bootstrap.py](../src/yield_curves/bootstrap.py), endpoint/Brent diagnostics test in [test_bootstrap.py](../tests/calibration/test_bootstrap.py) |
| Exact live/snapshot binding | Exact captured values, including hexadecimal floats/spline state, and serialized-byte checksums; no regression tolerance | [integration contract](integration_contract.md), [snapshots](snapshots.md) |

Solver termination and regression comparison do not replace financial acceptance.
Analytical helper tests use their own local `pytest.approx`/`assert_allclose`
settings; refer to the linked source rather than applying the regression numbers
to all products, representations or scenarios.

## Actual slow cases and fixture cost

The **27 slow cases** are the following 27 unparametrized functions, each
collecting exactly one case. All consumers of the three expensive module-scoped
fixtures are marked `slow`; the remaining helper/neutral-input cases in these two
modules stay non-slow. This describes construction cost, not a measured benchmark.
No slow tests are executed for this documentation change.

### [test_quote_sensitivity.py](../tests/research/test_quote_sensitivity.py)

`report`: One base + 15 one-sided sequential recalibrations; ten consumers. Frozen 15-quote synthetic data, projected 2026–2057 calendar, ±1 bp shocks (one-sided +1 bp for `report`), 28-day forwards with 7-day grid steps across the long horizon; no plotting.

- `test_one_perturbation_per_quote`
- `test_each_perturbation_contains_one_response_per_node`
- `test_upstream_nodes_are_invariant`
- `test_upstream_df_changes_are_numerically_negligible`
- `test_shocked_node_changes`
- `test_shocked_node_zero_rate_changes`
- `test_quote_bump_is_exactly_one_basis_point`
- `test_first_quote_shock_can_propagate_downstream`
- `test_last_quote_shock_leaves_all_previous_nodes_unchanged`
- `test_each_quote_shock_changes_forward_curve`

`central_report`: One base + 30 two-sided sequential recalibrations; seven consumers. Frozen 15-quote synthetic data, projected 2026–2057 calendar, ±1 bp shocks (one-sided +1 bp for `report`), 28-day forwards with 7-day grid steps across the long horizon; no plotting.

- `test_central_analysis_has_one_result_per_quote`
- `test_central_upstream_sensitivities_are_zero`
- `test_central_upstream_curvature_is_zero`
- `test_own_node_central_sensitivity_is_nonzero`
- `test_directional_responses_average_to_central_sensitivity`
- `test_forward_central_sensitivity_is_nonzero`
- `test_forward_curvature_is_finite`

### [test_global_sensitivity.py](../tests/research/test_global_sensitivity.py)

`cubic_global_report`: One base + 30 two-sided simultaneous cubic recalibrations; ten consumers. Frozen 15-quote synthetic data, projected 2026–2057 calendar, ±1 bp shocks (one-sided +1 bp for `report`), 28-day forwards with 7-day grid steps across the long horizon; no plotting.

- `test_global_sensitivity_report_metadata`
- `test_global_sensitivity_shock_identity_and_dimensions`
- `test_global_node_sensitivity_coordinates_are_consistent`
- `test_global_own_node_metrics_match_diagonal`
- `test_global_aggregate_node_sensitivity_metrics_are_consistent`
- `test_global_maximum_node_sensitivity_is_consistent`
- `test_perturbed_global_calibrations_succeed_and_reprice`
- `test_global_forward_observations_are_structurally_consistent`
- `test_global_forward_summary_matches_dense_observations`
- `test_global_forward_locality_metrics_are_valid`

## Audit observations and future work

These are bounded observations from source/test inspection, not established code
defects and not promises of additional current capability.

| ID | Identified evidence limit | Future work |
|---|---|---|
| T01 | [Realized compounding](../src/yield_curves/observations.py) guards empty observations, nonfinite fixings and nonpositive growth, but no direct tests of those guards or finite negative-fixing compounding were identified. Existing observation tests cover positive constant-rate compounding, weights and missing fixings. | Separately authorize focused realized-fixing edge-case tests and financial examples. |
| T02 | Snapshot tests interleave a reader and inject commit failures, but no simultaneous **independent publisher-process** integration test was identified. | Validate actual multi-process races if operational requirements demand it; retain local-POSIX/last-pointer-replacement-wins scope. |
| T03 | Smooth synthetic known-truth recovery and limited shocks do not establish broad market/scenario robustness. PCHIP implementation tests do not supply approved comparative selection evidence. | Separately scoped sparse/noisy/regime-changing and observed-market research, PCHIP comparisons and any new product/curve architecture validation. |

Use [extension roadmaps](extending.md) to separate future engineering and financial
validation. The canonical [evidence index](evidence/index.md) and
[reproduction levels](evidence/reproduce.md) retain C04 authority. This map does
not execute historical producers, generate reference candidates, establish
multi-curve/FX/XVA evidence or complete C06 distribution/release validation.
