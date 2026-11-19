# Data Inputs and Research Datasets

This directory contains **explicit financial inputs and frozen research datasets** used by the MXN F-TIIE OIS yield-curve implementation. It does not contain the analytical results generated from those inputs.

| Directory | Contents | Interpretation |
|---|---|---|
| [`calendars/`](calendars/README.md) | Explicit MXMC holiday data, including `mxmc_2026.csv` | Project mapping of sourced 2026 financial-market holidays; **not** a copy of CME's internal calendar |
| [`synthetic/`](synthetic/README.md) | `ftiie_ois_quotes_v1.csv` and its research specification | **Synthetic** OIS par quotations generated from a known reference curve; not observed market data |

## Input boundaries

The current standard curve builder accepts **in-memory OIS quotes and a business calendar**. CSV files are loaded through explicit adapters; the Python API does not select default inputs or independently determine whether quotes are genuine market observations.

The project records source declarations and file fingerprints separately from the financial values used in calibration. A `PROVIDED` calendar or `OBSERVED_MARKET_DATA` quote classification describes supplied provenance; **neither establishes independent verification of the underlying data**.

The verified 2026 holiday mapping and projected long-horizon calendar have different scopes. The projected calendar belongs to **research and demonstration**, not official future market data.

## Where outputs belong

- [Research outputs](../outputs/research/README.md) contain plots, numerical comparisons, and other analytical evidence generated from experiments.
- Operational curve archives are managed through the caller's selected output directory and the [snapshot contract](../docs/snapshots.md).

Frozen input datasets are kept separate from model outputs so experiments can clearly distinguish **supplied inputs, generated quotations, and recovered curves**.

[Quote and calendar input contract](../docs/input_contract.md) · [Financial conventions](../docs/conventions.md)
