# Archived Descriptive F-TIIE OIS Specification

[`mxn_ftiie_ois.yaml`](mxn_ftiie_ois.yaml) preserves a **readable, non-executable specification** of the project's F-TIIE OIS conventions and a sequential curve construction with **log-linear discount-factor interpolation**.

Its financial instrument descriptors remain useful for inspection, but the YAML file is **not loaded by the current baseline API, calibration functions, or command-line workflows**. In particular, its interpolation, validation, and method declarations are **not runtime configuration switches** and must not be used to infer the selected baseline's behavior.

The implemented consumer baseline uses **simultaneous nodal calibration with natural cubic interpolation of continuously compounded zero rates**. Alternative supported methods are selected through explicit Python functions and arguments.

For authoritative current behavior, consult [Financial conventions](../../docs/conventions.md), [Calibration methodology](../../docs/methodology.md), [Interpolation methods](../../docs/interpolation.md), and [Python integration](../../docs/integration_contract.md).

This archived file is kept for **traceability of descriptive specifications**, not as an input required to reproduce a curve.
