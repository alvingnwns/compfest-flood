# ARUNA Inventory Decision Suite — Iteration 1

Status: iteration 1 recorded; no tuning after the first finding has been performed.

Canonical result: `eval/results/inventory_iter1_20260926_144839.json`

Generated: 26 September 2026, 14:48 WIB

Suite: `inventory-decision-v1.1`

Cases: three fixed deterministic scenarios and four system executions, matching the legacy baseline structure.

## Metric definitions

- Service Level = Fulfilled Demand / Actual Demand × 100%.
- Unfulfilled Demand = Actual Demand − Fulfilled Demand.
- Total Operational Cost = Purchase Cost + Holding Cost + Stockout Cost + Waste Cost.
- Constraint Violation Rate = Violated Constraints / Total Constraints × 100%.

The fixed stockout cost is IDR 20,000 per unfulfilled cup, equal to the documented test selling price. Purchase cost comes from selected supplier packs. Holding and waste are zero and marked unevaluated because validated rates, shelf-life, and lot-age ground truth are unavailable.

## Aggregate KPI

The aggregate uses the primary run from each case, including the heavy variant for I03.

| Metric | Result |
| --- | ---: |
| Actual Demand | 1,186 cups |
| Fulfilled Demand | 563 cups |
| Service Level | 47.470489% |
| Unfulfilled Demand | 623 cups |
| Total Operational Cost | IDR 13,740,000 |
| Constraint Violation Rate | 0 / 79 = 0.0% |

### Operational cost breakdown

| Component | Result |
| --- | ---: |
| Purchase Cost | IDR 1,280,000 |
| Holding Cost | IDR 0 — unevaluated |
| Stockout Cost | IDR 12,460,000 |
| Waste Cost | IDR 0 — unevaluated |

Forecast diagnostics remain separate from business KPIs: MAE 2.686869 and RMSE 3.609751 cups per product-day.

## Test cases

| ID | Condition | Plan | Actual | Fulfilled | Service Level | Unfulfilled | Total Cost | CVR |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| I01 | Normal demand | COMPLETE | 377 | 377 | 100.000000% | 0 | IDR 800,000 | 0/36 |
| I02 | Impossible procurement | PARTIAL | 384 | 0 | 0.000000% | 384 | IDR 7,680,000 | N/A |
| I03 control | Standard constraints | COMPLETE | 425 | 424 | 99.764706% | 1 | IDR 720,000 | 0/36 |
| I03 heavy | Heavy constraints | PARTIAL | 425 | 186 | 43.764706% | 239 | IDR 5,260,000 | 0/43 |

I03 keeps the same actual demand for its control and heavy executions. Heavy constraints reduce Service Level by 56 percentage points, add 238 unfulfilled cups, and add IDR 4,540,000 operational cost.

## First finding

All generated recommendations obey their evaluated constraints, but operational effectiveness drops sharply under heavy constraints. The first iteration target is lead-time-aware procurement in I03: eligible supply is accepted within the 72-hour horizon without optimizing cumulative arrivals against each day of actual demand. No correction has been applied.
