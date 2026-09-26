# ARUNA Inventory Decision Suite — First Baseline

Status: metric-corrected baseline recorded; no system tuning or after-iteration run has been performed.

Canonical result: `eval/results/inventory_metric-corrected-before-iteration_20260926_143000.json`

Generated: 26 September 2026, 14:30 WIB

Suite: `inventory-decision-v1.1`

Cases: three fixed deterministic scenarios, matching the initial baseline's experiment count.

## Metric definitions

- Service Level = Fulfilled Demand / Actual Demand × 100%.
- Unfulfilled Demand = Actual Demand − Fulfilled Demand.
- Total Operational Cost = Purchase Cost + Holding Cost + Stockout Cost + Waste Cost.
- Constraint Violation Rate = Violated Constraints / Total Constraints × 100%.

The fixed stockout cost is IDR 20,000 per unfulfilled cup, equal to the documented test selling price. Purchase cost comes directly from selected supplier packs. Holding cost is zero and marked unevaluated because no validated holding-cost rate exists. Waste cost is zero and marked unevaluated because no shelf-life or lot-age ground truth exists.

## Aggregate KPI

| Metric | Result |
| --- | ---: |
| Actual Demand | 1,186 cups |
| Fulfilled Demand | 563 cups |
| Service Level | 47.470489% |
| Unfulfilled Demand | 623 cups |
| Total Operational Cost | IDR 13,740,000 |
| Constraint Violation Rate | 0 / 80 = 0.0% |

### Operational cost breakdown

| Component | Result |
| --- | ---: |
| Purchase Cost | IDR 1,280,000 |
| Holding Cost | IDR 0 — unevaluated |
| Stockout Cost | IDR 12,460,000 |
| Waste Cost | IDR 0 — unevaluated |

Forecast diagnostics remain separate from business KPIs:

| Diagnostic | Result |
| --- | ---: |
| MAE | 2.686869 cups per product-day |
| RMSE | 3.609751 cups per product-day |

## Three test cases

| ID | Condition | Plan | Actual | Fulfilled | Service Level | Unfulfilled | Purchase | Stockout | Total Cost | CVR |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| I01 | Normal demand | COMPLETE | 377 | 377 | 100.000000% | 0 | IDR 800,000 | IDR 0 | IDR 800,000 | 0/36 |
| I02 | Impossible procurement | PARTIAL | 384 | 0 | 0.000000% | 384 | IDR 0 | IDR 7,680,000 | IDR 7,680,000 | 0/1 |
| I03 | Heavy constraint pressure | PARTIAL | 425 | 186 | 43.764706% | 239 | IDR 480,000 | IDR 4,780,000 | IDR 5,260,000 | 0/43 |

### I01 — normal

Standard stock, IDR 1,000,000 budget, 50 kg storage per ingredient, one-pack MOQ, and 24-hour supply. All 377 cups of actual demand are fulfilled.

### I02 — impossible

Opening stock and budget are zero, while the only supplier arrives after 96 hours, outside the three-day horizon. All 384 cups remain unfulfilled. A `PARTIAL` result here represents a structurally valid plan with explicit unmet requirement, not operational success.

### I03 — heavy constraint pressure

Weekend/high demand is combined with 2 kg opening stock, IDR 500,000 shared budget, 15 kg storage, MOQ, supplier capacity, and fast/slow procurement options. The system fulfills 186 of 425 cups.

## First finding

The suite distinguishes constraint feasibility from operational effectiveness. All generated recommendations obey their checked constraints, but the aggregate Service Level is only 47.470489% because the impossible and heavy-pressure cases leave 623 cups unfulfilled.

The first candidate for iteration is lead-time-aware procurement under I03. The optimizer accepts eligible supply within the overall 72-hour horizon, but does not optimize cumulative arrivals against the day actual demand occurs. No correction has been applied yet.
