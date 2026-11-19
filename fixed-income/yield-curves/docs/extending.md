# Extending Financial Methods and Curve Architectures

This guide describes the **financial specifications, implementation contracts, and validation evidence** needed to extend the MXN F-TIIE OIS curve project. These are **potential extensions**, not capabilities already available or a committed development roadmap.

Adding an interpolation method, supporting another instrument, and introducing a collateral-specific multi-curve architecture are different problems. Each requires a financial justification, explicit changes to code and interfaces, and independent testing appropriate to the proposed use.

The current selected baseline calibrates **F-TIIE OIS only** with simultaneous nodal calibration and natural cubic interpolation of continuously compounded zero rates. Alternative curve representations are available for compatible research or construction purposes, but their existence does not confer baseline acceptance or publication authority. Internal factories and capability tables are not general-purpose plug-in registries.

See [Methodology](methodology.md), [Conventions](conventions.md), [Architecture](architecture.md), [Input contract](input_contract.md) and [Limitations](assumptions_limitations.md). Existing versioned policies, frozen datasets and snapshot identities remain distinct.

## Extending interpolation methods

### Current capability

[`curves.py`](../src/yield_curves/curves.py) provides four nodal representations:
log-linear DF, linear continuous zero, natural cubic continuous zero and PCHIP
continuous zero. The [interpolation specification](interpolation.md) describes
them. [`engine_capabilities.py`](../src/yield_curves/engine_capabilities.py)
explicitly supports the first two in both engines, and cubic/PCHIP in simultaneous
calibration only. PCHIP is implemented as an experimental representation; it is
not the approved operational baseline or part of the existing selection conclusion.

### Implementation requirements

| Review surface | Change/design required |
|---|---|
| [`curves.py`](../src/yield_curves/curves.py) | Define interpolated quantity, node state, origin anchor, supported dates, derivatives, DF/zero/forward identities and numerical guards. Extend `CurveInterpolationMethod`, the `NodalCurve` union and `build_nodal_curve`; an enum value alone is insufficient. |
| [`engine_capabilities.py`](../src/yield_curves/engine_capabilities.py) | Add explicit compatibility for each engine, retaining immutability and exhaustive enum coverage. This table authorizes caller-selected methods; it does not register factories or select policy. |
| [`bootstrap.py`](../src/yield_curves/bootstrap.py) | Review candidate-curve construction and scalar objective. Sequential support requires demonstrated freeze-and-append compatibility: a later pillar must not change previously fitted instruments. Global spline coupling cannot be approved by toggling a flag. |
| [`calibration.py`](../src/yield_curves/calibration.py) | Review log-DF objective, curve factory, residual units, DF bounds, initialization and solver behavior. Preserve explicit-start rejection/no-fallback semantics. Default log-linear initialization need not change merely because the final representation changes. |
| [`baseline.py`](../src/yield_curves/baseline.py) | Distinguish representation support from operational adoption. The current baseline selects cubic and checks the actual curve class. New operational adoption needs construction/acceptance policy, geometry and complete live value-binding design; cubic spline-state capture is currently specific to cubic. |
| [`execution.py`](../src/yield_curves/execution.py) | Design supported-policy identity, construction history, provenance/value binding and standard publication authority for any new operational baseline. |
| [`snapshot_assurance.py`](../src/yield_curves/snapshot_assurance.py) and [`snapshots.py`](../src/yield_curves/snapshots.py) | Assurance currently reconstructs cubic under supported historical V1 rules. Specify persistence/reconstruction, policy/schema compatibility, rejection of unsupported history and no-solve checks before promising operational delivery. |
| [`tests/`](../tests/) and documentation | Add representation and engine evidence, acceptance/binding/publication/assurance contracts if adopted; update interpolation, methodology, limitations and test navigation. Keep explicit two-/three-method research comparison sets deliberate. |

### Financial validation requirements

Prove node reproduction and DF/zero/forward relationships across the supported
domain. Assess shape, origin behavior, smoothness, locality, negative-rate and
sparse/noisy-input behavior appropriate to the proposed method. Compare
independent repricing, recovery and sensitivities under explicitly identified
scenarios. Strong synthetic fit alone cannot justify operational selection.
The existing [methodology](evidence/methodology.md) and [risk](evidence/risk.md)
evidence supports only the studied scenarios and does not validate a proposed extension.

Maintainer checklist:

- [ ] Specify representation math/domain and implement enum, type union and factory.
- [ ] Demonstrate each proposed engine capability, warm starts and failure behavior.
- [ ] Test node/origin/forward identities, malformed geometry, nonfinite/nonpositive
  factors, domain rejection and applicable shape/locality invariants; see the
  [curve](test-coverage-map.md#curve-interpolation) and
  [engine](test-coverage-map.md#simultaneous-calibration) contracts.
- [ ] If proposing operational adoption, design acceptance, live binding,
  supported-policy publication and persisted no-solve assurance together.
- [ ] Document financial validation scope and review numerical changes through
  [candidate maintenance](../scripts/tests/README.md), without automatic fixture replacement.

## Supporting another financial instrument

### Current capability

The baseline accepts **F-TIIE OIS quotes only**. The four-field
[`OISCalibrationQuote`](../src/yield_curves/quotes.py) protocol is an OIS contract,
not a multi-product interface. [`quote_io.py`](../src/yield_curves/quote_io.py)
accepts only `PAR_OIS_RATE` when quote type is supplied; current preparation,
engines and shared repricing rebuild Core-v1 OIS. Conventions form a closed
profile, floating spread is zero, and calibration uses unit notional.
A downstream position's positive notional scales valuation; it is conceptually
separate from the calibration notional and does not extend the product profile.

### Implementation requirements

| Contract | Required design and implementation review |
|---|---|
| Quote identity | Product/type, financial fields, labels, units, sign conventions and distinction between a rate, price, spread or basis quote. Do not reinterpret OIS fields silently. |
| Input schema and provenance | Product-aware in-memory/CSV contracts, validation, ordering, source classification and raw-byte provenance; review `quotes`, `quote_io`, `inputs` and CLI adapters. |
| Conventions and dates | Product-specific supported profile, calendars/coverage, spot/payment/fixing rules, schedules/stubs and observation mechanics in `conventions`, `calendars`, `schedules`, `observations`, `instruments`. |
| Cash flows and pricing | Explicit representation, currency, accrual/compounding, cash-flow signs, projection/discount requirements and position-notional scaling in `instruments`/`pricing`. |
| Calibration | Residual units/objective, admissible bounds, curve reference date and pillar assignment, instrument dependencies and engine compatibility in `bootstrap`/`calibration`. |
| Independent repricing | Reconstruct the product from quotes and reprice final curves without trusting stored solver residuals; extend `repricing` deliberately. |
| Acceptance | Product-specific input/structural/fit and economic checks; clarify which policy can accept it. Current cubic OIS baseline must not silently become multi-product. |
| Execution and snapshot compatibility | Financial-context/policy identity, heterogeneous input serialization, source capture, payload/live binding, publication authority and archived schema/policy reconstruction in `baseline`, `execution`, `snapshots`, `snapshot_assurance`. |

### Financial validation requirements

Establish contractual date/cash-flow examples, pricing identities and numerical
references for the new product, including relevant zero/negative-rate, stub,
fixing, holiday and scale edge cases. Validate residual and pillar choices,
identifiability, independent fit and sensitivities with credible product-specific
evidence. Adding classes or passing unit tests does not establish market
conventions or justify reusing OIS acceptance thresholds.

Maintainer checklist:

- [ ] Define quote/input/provenance and supported convention profiles before wiring engines.
- [ ] Implement schedules, observations/cash flows, instrument and explicit-curve pricing.
- [ ] Design pillar assignment, residuals, independent repricing and acceptance.
- [ ] Test unit financial identities, malformed-input rejection, integration across
  preparation/engine/repricing, and independent numerical benchmarks.
- [ ] Design execution binding and compatible persisted reconstruction before publication.
- [ ] Update conventions, inputs, integration, validation, snapshots and
  [test contracts](test-coverage-map.md#instrument-and-pricing); review frozen candidates manually.

## Introducing multi-curve construction

### Current capability

[`pricing.calculate_par_rate`](../src/yield_curves/pricing.py) and
`value_ftiie_ois` already accept separate `projection_curve` and `discount_curve`
parameters implementing the minimal `DiscountFactorCurve` protocol.
[`test_projection_and_discount_curves_are_separable`](../tests/unit/test_pricing.py)
uses different flat curves. This pricing seam is useful, while current solvers,
shared repricing and operational policy still pass the **same curve** for both
roles. There is no integrated multi-curve, FX-basis or XVA implementation/evidence.

### Implementation requirements

| Area | Missing work |
|---|---|
| Curve roles/dependencies | Define curve identifiers, reference dates, currencies, role-specific queries, dependency graph and ownership of externally supplied versus calibrated curves. |
| Multi-curve calibration | Product-to-curve residual dependencies, ordered or joint construction, conditioning/initialization and independent portfolio/product repricing. Replace implicit same-curve assumptions explicitly. |
| Collateral/CSA discounting | Specify collateral currency, CSA terms, discount-curve selection and economically consistent discount/projection separation. |
| Multi-currency dates and FX | Currency calendars/spot lags/joint business-day rules, FX quote units, FX instruments and settlement/discount relationships. |
| Cross-currency basis | Product/cash-flow representation, basis conventions/placement and calibrated dependencies; separate from a simple same-curve quote shock. |
| Input/source contracts | Per-curve/per-product valuation context, synchronized dates, provenance and incomplete/inconsistent dataset rejection. |
| Acceptance and sensitivity | Role-specific structure/fit, cross-curve consistency, dependency propagation, shock definitions, risk units and multi-curve sensitivity evidence. |
| Snapshot provenance/versioning | Persist the complete graph, nodes, inputs, policies, source identities and external dependencies; bind and reconstruct historical meaning without solving. Govern schema/policy compatibility rather than relabeling schema `3.0`/V1. |

### Financial validation requirements

Specify the intended collateral and market architecture, validate instruments
and no-arbitrage relationships, and test curve dependency and shock transmission.
Obtain suitable observed-market and scenario evidence before claiming broad
robustness or institutional replication. Current synthetic same-curve research
cannot validate FX basis, cross-currency discounting or XVA; XVA would require its
own separately scoped valuation/risk design and evidence.

Maintainer checklist:

- [ ] Specify curve roles, financial assumptions, product/input dependencies and CSA scope.
- [ ] Implement explicit multi-curve pricing/construction/repricing with coherent dates.
- [ ] Test same-curve reduction, distinct-role behavior, dependency ordering, missing
  curve/input rejection and independent numerical cross-checks.
- [ ] Validate calibration identifiability, cross-curve acceptance and sensitivities.
- [ ] Design bound multi-curve archives and no-solve assurance before operational adoption.
- [ ] Revise architecture, methodology, conventions, limitations, API/input/snapshot
  contracts and test map with reviewed evidence and explicit version decisions.

## Validation and reference discipline

Use existing Python 3.11 and the [testing guide](testing.md) for marker/cost
selection. A source function, a parametrized collected case and an executed pass
are different evidence. Preserve expensive-fixture marker rules and the
exclusive-candidate/human numerical-review workflow. Documentation of a future
roadmap is not authorization to implement it or certification of its financial
results. Future work requires evidence appropriate to its financial claims.
