# Changelog

## 0.1.0

- Added reusable MXN F-TIIE OIS conventions, calendars, schedules, observations, instruments, pricing, and curve representations.
- Added historical sequential bootstrap and simultaneous nodal calibration engines.
- Added log-linear DF, linear continuous-zero, cubic continuous-zero, and PCHIP continuous-zero implementations.
- Added validation, independent repricing, recovery, curve diagnostics, and quote-sensitivity infrastructure.
- Selected simultaneous nodal calibration with `CUBIC_CONTINUOUS_ZERO` as the current project baseline.
- Added the stable `yield_curves.baseline` API and explicit `accepted_for_use` acceptance contract.
- Added operational baseline snapshots under `outputs/baseline/`.
- Reorganized historical workflows under `scripts/experiments/` and separated operational and assurance entrypoints.
- Documented the operational, assurance, and research boundaries and the current project limitations.
