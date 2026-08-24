# Dynamic Hazard Phase 5A: Supply-Chain Propagation Validation

This directory contains reproducible, research-only evidence that the frozen dynamic
hazard runtime propagates through existing NetworkX routing, disruption analysis,
OR-Tools CP-SAT recovery, manufacturing, logistics, commerce, and KPI computation.
No frontend, optimizer objective, optimizer constraint, routing algorithm, model, or
runtime hazard formula is changed in this phase.

## Controlled matrix

The analysis runs Q1, Q2, Q3, and Q4 under four existing operational presets:

- Normal: no overrides.
- Kendaraan Terbatas: vehicle V-03 unavailable.
- Stok Gudang Kritis: Product A inventory at both warehouses set to 50.
- Gangguan Operasional Berat: V-01 and V-02 unavailable, and East Warehouse Product A
  inventory set to zero.

Only the rainfall scenario varies within each operational-condition comparison.
Hazard metadata remains identical across operational conditions, while vehicle and
inventory state remains identical across Q1-Q4 for a fixed condition.

## Routing-to-optimizer contract

The existing optimizer receives more than a route ID:

- recovery routes replace baseline routes when NetworkX provides an alternative;
- critical-band recovery routes are excluded;
- route ETA affects delay and optional maximum-delay feasibility;
- routing-band rank contributes the existing risk penalty;
- route distance and vehicle cost contribute the existing transport penalty; and
- baseline supplier-route bands scale material availability before BOM constraints.

Therefore observed business changes arise from existing dynamic road-risk and routing
consequences. No scenario-specific delay or business-impact rule is fabricated.

## Artifacts

- `propagation_matrix.json`: detailed provenance and outputs for all 16 combinations,
  the optimizer contract, integrity checks, and historical regression.
- `propagation_matrix.csv`: compact comparison of hazard, roads, routes, recovery, KPI,
  and binding classification.
- `causal_traces.json`: Q1-relative route, assignment, production, disruption, and KPI
  state transitions.
- `decision_gate.json`: evidence checks and the Phase 5B decision.

## Interpretation

Hazard and road-risk scores are strictly monotonic, but discrete optimizer decisions
and KPI outcomes need not be. `BINDING` means production or KPI changed relative to Q1;
`PARTIALLY_BINDING` means CP-SAT assignments changed while headline KPI was buffered;
`NON_BINDING` identifies the Q1 within-condition reference or an unchanged recovery
plan. The severe-disruption preset is predominantly constrained by its single
available vehicle and zero East Warehouse Product A stock, so rainfall changes routes
and assignments without changing its KPI totals.

All hazard and dynamic road-risk values remain uncalibrated relative scores, not road
flood probabilities, guaranteed floods, closure forecasts, or real-time forecasts.

## Reproduce

From `be`:

```powershell
$env:PYTHONPATH = 'scripts'
python -m dynamic_hazard.analyze_supply_chain_propagation
```

The script clears only the process-local simulation repository before and after the
run. It writes no runtime state and produces byte-identical evidence artifacts for the
same frozen inputs and dependency versions.
