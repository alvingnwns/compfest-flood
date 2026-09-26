# ARUNA Inventory Decision Suite — Iteration 2

Status: iteration 2 recorded against the frozen Iteration 1 protocol. No testcase input, actual demand, metric formula, simulator rule, dataset, or forecast artifact was changed.

Generated: 26 September 2026, 16:08 WIB

Suite: `inventory-decision-v1.1` · Optimizer: `time-indexed-lexicographic-v2` · Forecast artifact: `juice-xgb-direct-v1` (unchanged)

## Artifacts

| Purpose | Path |
| --- | --- |
| Iteration 1 (frozen) | `eval/results/inventory_iter1_20260926_144839.json` |
| Iteration 2 | `eval/results/inventory_iter2_20260926_160545.json` |
| Iteration 2 determinism rerun | `eval/results/inventory_iter2-determinism-rerun_20260926_160548.json` |
| Iter1 → Iter2 like-for-like comparison | `eval/results/compare_inventory_iter1_iter2_20260926_160645.json` |
| Guarded legacy bridge (Iter2) | `eval/results/bridge_legacy_inventory_20260926_160850.json` |

The two suite runs produce identical canonical decision hashes and KPIs for every run.

## What changed

1. **Time-indexed procurement (I2.1)** — production `optimize_procurement` now keeps a daily inventory balance per ingredient, credits each offer only on its arrival day, and has daily served and shortage variables. Budget, MOQ, pack size, supplier capacity, integer packs and the 72-hour horizon remain hard constraints. Storage is enforced without crediting forecast consumption, so a plan remains physically feasible even when demand is lower than predicted; this is also exactly the storage rule the evaluator checks.
2. **Sequential lexicographic objectives** — four CP-SAT passes, each fixing the previous optimum as a hard bound instead of mixing arbitrary weights: (1) lost-sales value of daily shortage, (2) priority/day urgency tie-break, (3) ending safety-stock deficit, (4) purchase cost. Every stage proves `OPTIMAL` in all runs. Quantities are rescaled per ingredient by their exact GCD, and the solver uses one worker with full LP linearization for determinism.
3. **Granular priority (I2.2)** — the risk engine adds an internal deterministic rank from first stockout day, lost-sales value of the unreplenished shortfall, shortfall share, D+1 requirement value, and validation-split MAE uncertainty. Public risk enums and fields are unchanged; the rank feeds the optimizer tie-break and recommendation ordering.
4. **Hindsight oracle (I2.3, evaluation only)** — `eval/oracle.py` solves the same testcase constraints with actual demand after the system decision is fixed, then replays its purchases through the same simulator. It reports `feasibleFulfillmentPercent`, `serviceRegretCups` and `operationalCostRegretIdr`. It is never imported by `be/`.

## Aggregate KPI (primary runs)

| Metric | Iter1 | Iter2 | Delta |
| --- | ---: | ---: | ---: |
| Actual demand | 1,186 cups | 1,186 cups | — |
| Fulfilled demand | 563 cups | 582 cups | +19 |
| Service Level | 47.470489% | 49.072513% | +1.602024 pp |
| Unfulfilled demand | 623 cups | 604 cups | −19 |
| Total Operational Cost | IDR 13,740,000 | IDR 13,360,000 | −IDR 380,000 |
| Constraint Violation Rate | 0 / 79 = 0% | 0 / 79 = 0% | 0 |
| Feasible fulfillment (vs oracle 585 cups) | 96.239316% | 99.487179% | +3.247863 pp |
| Service regret | 22 cups | 3 cups | −19 |
| Operational cost regret (vs oracle IDR 13,000,000) | IDR 740,000 | IDR 360,000 | −IDR 380,000 |

Forecast diagnostics are unchanged because the forecast is unchanged: MAE 2.686869 and RMSE 3.609751 cups per product-day.

## Per run

| Run | Actual | Oracle max | Iter1 fulfilled | Iter2 fulfilled | Iter2 SL | Iter2 cost | Iter2 feasible fulfillment | Iter2 service regret | CVR | Decision changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| I01 normal | 377 | 377 | 377 | 377 | 100% | IDR 800,000 | 100% | 0 | 0/36 | No |
| I02 impossible | 384 | 0 | 0 | 0 | 0% | IDR 7,680,000 | N/A (0/0) | 0 | N/A | No |
| I03 control | 425 | 425 | 424 | 424 | 99.764706% | IDR 720,000 | 99.764706% | 1 | 0/36 | No |
| I03 heavy | 425 | 208 | 186 | 205 | 48.235294% | IDR 4,880,000 | 98.557692% | 3 | 0/43 | Yes |

I03 control-to-heavy sensitivity is now −51.53 pp Service Level, +219 unfulfilled cups and +IDR 4,160,000 (Iter1: −56 pp, +238 cups, +IDR 4,540,000). The heavy case still has a physical ceiling of 48.94%, so its absolute Service Level remains low by construction.

## Interpretation

- **The whole Iter1→Iter2 gain comes from I03 heavy**, the only run where arrival timing and a binding budget interact. I01, I02 and I03 control produce byte-identical decisions, so the change does not regress the nominal or impossible cases.
- **Remaining heavy regret (3 cups) is forecast-driven, not optimizer-driven.** The oracle buys two slow packs for `ING-011` and none for `ING-001`; actual P011 demand on day 2 was 26 cups against a forecast of 11. The optimizer is solved to proven optimality on the forecast it receives.
- **Operational cost regret is dominated by safety-stock policy.** In I01 (IDR 300,000) and I03 control (IDR 200,000) the system deliberately buys up to the 3 kg safety stock. The cost KPI charges the purchase but assigns no value to the stock left at day 3, while the hindsight oracle ignores safety stock. This regret is a policy choice, not a solver defect, and should not be optimized away against the frozen cases.
- **Bridge.** The guarded bridge still forbids causal cross-track claims. On the heavy archetype the inventory track reports 48.24% against legacy 66.45%; this reflects the inventory scenario's 48.94% physical ceiling and a different domain, not evidence that either system is better.

## Production behaviour notes

- In production, arrival day is the WIB business date of `generatedAt + leadTimeHours`. With the seeded 24-hour supplier, an order generated on D+1 lands on D+2, so D+1 demand must be served from current stock. The evaluator keeps its frozen semantics (orders placed at the close of the as-of day).
- Plans are fingerprinted with the optimizer version, so Iteration 1 plans persisted for identical inputs are not reused.
- A rollback-only smoke against the Supabase schema exercised forecast → risk → CP-SAT → recommendation persistence with deterministic explanations: `OPTIMAL / COMPLETE`, priority-ordered recommendations, approved inbound credited, `_base` absent from public risk payloads, and nothing committed.

## Verification

- `pytest be/tests/test_inventory_product_track.py be/tests/test_inventory_eval_oracle.py`: 25 passed (14 existing + 11 new covering arrival-day crediting, storage, MOQ/safety ordering, cost tie-break, budget with reservation, daily balance with non-divisible quantities, determinism, priority ranking, WIB arrival day, and oracle bounds/regret).
- `ruff check` passes for every changed file. `eval/run_eval.py` (legacy suite, untouched) reports nine pre-existing findings under the installed ruff 0.16.9.
- `compileall` passes for `be/app` and `eval`.

## Safe reporting language

> Iteration 2 replaces the aggregate 72-hour procurement model with a time-indexed, lexicographically optimized CP-SAT model on the same frozen cases, forecast, and simulator. Aggregate Service Level rises from 47.47% to 49.07%, unfulfilled demand falls by 19 cups, and operational cost falls by IDR 380,000 with zero constraint violations. Under heavy constraints the system now reaches 98.56% of the hindsight fulfillment ceiling (from 89.42%); the remaining 3-cup gap is attributable to forecast error. Cross-domain superiority over legacy ARUNA is still not proven.

## Next steps

1. **I2.4 forecast uncertainty** — derive buffers or quantile models from validation residuals only (rolling-origin if time permits); never tune on the frozen cases or the test split.
2. Optional independent HiGHS (`scipy.optimize.milp`) benchmark of the same formulation; no KPI change is expected.
3. Persist the optimizer `dailyPlan` if the owner UI or Qwen explanation needs day-level shortage context.
