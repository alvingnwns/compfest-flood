# ARUNA Baseline Legacy vs Iteration 1 metric bridge

Objective: compare the old ARUNA stock recovery decision system without AI forecasting/reasoning against the new ARUNA inventory and procurement system in iteration 1.

Artifacts:

- Legacy canonical: `eval/results/baseline_20260926_111142.json`
- Iteration 1: `eval/results/inventory_iter1_20260926_144839.json`
- Bridge output: `eval/results/bridge_legacy_inventory_20260926_144921.json`

The baseline artifact remains unchanged. The bridge recalculates both tracks with the same formulas and pairs three scenario archetypes. The comparison is contextual because the systems still use different input domains and demand units. It cannot establish causal improvement as if both systems had processed identical input rows.

The legacy recovery engine uses deterministic CP-SAT/OR-Tools optimization. Here, `non-AI` means it has no XGBoost demand forecast and no Qwen reasoning layer; it does not mean the legacy system lacks an optimizer.

## Shared formulas

- Service Level = Fulfilled Demand Units / Actual Demand Units × 100%.
- Unfulfilled Demand = Actual Demand Units − Fulfilled Demand Units.
- Total Operational Cost = Purchase + Holding + Stockout + Waste.
- Constraint Violation Rate = Violated Constraints / Evaluated Constraints × 100%.
- CVR is N/A when no decision exists and zero constraints can be evaluated.

The bridge changes the legacy Service Level view from fully fulfilled orders to fulfilled demand units. The original 7/20 and 8/20 order-level KPIs remain in the legacy artifact.

## Matched test structure

| Bridge case | Legacy source | Inventory source |
| --- | --- | --- |
| B01 Normal | C1 Q2 recovery | I01 normal demand |
| B02 Impossible | C2 Q2 no-feasible-plan | I02 impossible procurement |
| B03 Heavy pressure | C5 Q4 recovery | I03 heavy constraints |

Both suites now contain three cases and four system executions. Their sensitivity cases use fixed ground truth within each track: control followed by stress.

## Formula-aligned scorecard

| Case | Track | Service Level | Unfulfilled rate | Cost / demand value | CVR |
| --- | --- | ---: | ---: | ---: | ---: |
| Normal | Legacy recovery | 72.688172% | 27.311828% | 25.870743% | 0.0% |
| Normal | Inventory iter1 | 100.000000% | 0.000000% | 10.610080% | 0.0% |
| Impossible | Legacy recovery | 0.000000% | 100.000000% | 100.000000% | N/A |
| Impossible | Inventory iter1 | 0.000000% | 100.000000% | 100.000000% | N/A |
| Heavy | Legacy recovery | 66.451613% | 33.548387% | 31.347569% | 0.0% |
| Heavy | Inventory iter1 | 43.764706% | 56.235294% | 61.882353% | 0.0% |

## Matched sensitivity

| Track | Control → stress | Service Level delta | Unfulfilled delta | Operational cost delta |
| --- | --- | ---: | ---: | ---: |
| Legacy | C5 Q1 → Q4 | −6.236559 pp | +145 units | +IDR 6,550,000 |
| Inventory | I03 control → heavy | −56.000000 pp | +238 cups | +IDR 4,540,000 |

## Safe interpretation

- Normal and impossible archetypes align directionally.
- Inventory iteration 1 is weaker on normalized heavy-pressure Service Level and cost-to-demand-value measures. This is the clearest iteration target.
- Absolute demand and IDR totals cannot be subtracted across tracks because their products, units, constraints, and simulated operations differ.
- Legacy operational cost contains only its sales-exposure stockout proxy. Purchasing, holding, and waste were not modeled.
- Inventory purchase and stockout costs are evaluated. Holding and waste remain unevaluated because rates and shelf-life data are absent.
- Cross-track deltas are descriptive and carry `causalImprovementClaimAllowed: false`.
