# ARUNA Iteration 2 Handoff

Generated: 26 September 2026, 15:25 WIB

## Repository state

- Working branch: `dev/iter2`
- HEAD: `aa33a81e8422881f7183b9e3c29823bb261841e9`
- `dev/iter2` was created directly from `dev/phase2` with no code changes.
- `main`, `dev/phase2`, `origin/main`, and `origin/dev/phase2` point to `aa33a81`.
- Remote annotated tag `checkpoint-2-iteration` points to commit `aa33a81`.
- Checkpoint 1 tag: `checkpoint-1-baseline` at `ab2575d`.
- Working tree was clean before this handoff file was created.
- `dev/iter2` has not been pushed.

Do not rewrite checkpoint artifacts or change fixed testcase inputs to improve scores. Iteration 2 must start from the frozen Phase 2 results.

## Iteration 2 progress (26 September 2026, 16:10 WIB)

| Item | Status |
| --- | --- |
| I2.1 Time-indexed procurement | Done in production `optimization.py` (`time-indexed-lexicographic-v2`), four sequential CP-SAT stages, all `OPTIMAL`. |
| I2.2 Granular risk priority | Done in `risk.py` (`project_daily`, `priority_key`, `assign_priorities`); internal only, public enums unchanged. |
| I2.3 Oracle metrics | Done in `eval/oracle.py`, wired into `eval/suite.py`; like-for-like comparison in `eval/compare.py`. |
| I2.4 Forecast uncertainty | Not started. Remaining heavy regret (3 cups) is forecast-driven. |
| I2.5 Qwen boundary | Unchanged; Qwen still only explains persisted solver output. |

Iter2 artifact: `eval/results/inventory_iter2_20260926_160545.json`. Findings: `eval/INVENTORY_ITER2_FINDINGS.md`. Aggregate Service Level 47.470489% → 49.072513%, operational cost IDR 13,740,000 → 13,360,000, CVR 0/79, heavy feasible fulfillment 89.42% → 98.56%. Changes are uncommitted on `dev/iter2`.

Local note: `pytest.exe` and `ruff.exe` may be blocked by Windows Application Control; use `python -m pytest` and `python -m ruff`.

## Product objective

The new product track is:

```text
POS transaction
  -> persistent sales and inventory
  -> XGBoost demand forecast D+1/D+2/D+3
  -> BOM conversion
  -> deterministic inventory risk engine
  -> OR-Tools procurement optimization
  -> Qwen explanation
  -> owner decision
  -> goods receipt
```

Technology:

- Python, FastAPI, Pydantic.
- PostgreSQL through Supabase, isolated schema `aruna_inventory`.
- XGBoost direct-horizon forecasting.
- Deterministic risk rules.
- OR-Tools CP-SAT procurement.
- Qwen structured explanation with deterministic fallback.
- Business dates and monthly boundaries use Asia/Jakarta.
- Activity logs cover important mutations and use monthly WIB partitions.

Credentials remain in `.env`. Never print or commit them. Supabase migration and seed were already run successfully.

## Phase 2 implementation status

Implemented under `be/`:

- PostgreSQL migration, seed, ledger, idempotency, row locking, inventory versioning.
- Products, ingredients, BOM, suppliers/offers, POS sales, void, stocktaking, receiving.
- Forecast persistence and inference.
- Inventory risk engine.
- Procurement plan generation, approval/rejection, stale-plan checks, receiving.
- Qwen explanation and deterministic fallback.
- Dashboard and FE-facing API contract.

Primary references:

- `be/be-rework-todo.md`
- `be/docs/INVENTORY_BACKEND_CONTRACT.md`
- `be/docs/INVENTORY_SETUP.md`
- `be/docs/INVENTORY_MODEL_REPORT.md`
- `be/docs/INVENTORY_DEMO_ASSUMPTIONS.md`
- `eval/INVENTORY_BASELINE_FINDINGS.md`
- `eval/INVENTORY_BRIDGE_REPORT.md`

Previous verification:

- Product-track tests: 14 passed.
- Lint and compile checks passed.
- Full backend regression: 140 passed, 11 failed. Four failures were pre-existing legacy recovery semantics/validation expectations; seven required an absent Dynamic Hazard source ZIP.

## Frozen evaluation protocol

The inventory suite follows:

```text
fixed testcase
  -> system decision
  -> simulator applies decision to actual demand
  -> operational KPI
```

Primary metrics:

1. `Service Level = Fulfilled Demand / Actual Demand * 100%`
2. `Unfulfilled Demand = Actual Demand - Fulfilled Demand`
3. `Total Operational Cost = Purchase + Holding + Stockout + Waste`
4. `Constraint Violation Rate = Violations / Evaluated Constraints * 100%`

MAE and RMSE are diagnostics only.

Canonical artifacts:

- Legacy baseline: `eval/results/baseline_20260926_111142.json`
- Inventory Iter1: `eval/results/inventory_iter1_20260926_144839.json`
- Guarded bridge: `eval/results/bridge_legacy_inventory_20260926_144921.json`

The legacy and inventory tracks use different operational domains and demand units. The bridge aligns formulas and scenario archetypes but does not prove causal improvement. Do not present absolute cross-track demand or IDR deltas as an apples-to-apples result.

## Iter1 KPI

Aggregate primary runs:

| Metric | Result |
| --- | ---: |
| Actual demand | 1,186 cups |
| Fulfilled demand | 563 cups |
| Service Level | 47.470489% |
| Unfulfilled demand | 623 cups |
| Purchase cost | IDR 1,280,000 |
| Stockout cost | IDR 12,460,000 |
| Total Operational Cost | IDR 13,740,000 |
| CVR | 0 / 79 = 0% |
| Forecast MAE | 2.686869 cups/product-day |
| Forecast RMSE | 3.609751 cups/product-day |

Cases:

| Case | Actual | Fulfilled | Service Level | Unfulfilled | Cost | CVR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| I01 normal | 377 | 377 | 100% | 0 | IDR 800,000 | 0/36 |
| I02 impossible | 384 | 0 | 0% | 384 | IDR 7,680,000 | N/A |
| I03 control | 425 | 424 | 99.764706% | 1 | IDR 720,000 | 0/36 |
| I03 heavy | 425 | 186 | 43.764706% | 239 | IDR 5,260,000 | 0/43 |

I03 control-to-heavy delta:

- Service Level: -56 percentage points.
- Unfulfilled demand: +238 cups.
- Operational cost: +IDR 4,540,000.

I02 is intentionally impossible: zero initial stock, zero budget, and only a 96-hour supplier outside the 72-hour horizon. Zero fulfillment is correct safe behavior.

## How decisions are produced

- XGBoost predicts demand only.
- The deterministic risk engine derives shortfall, projected stockout, and reason codes.
- OR-Tools CP-SAT selects supplier offers and integer pack counts under budget, MOQ, pack size, capacity, storage, and horizon constraints.
- Qwen explains structured results and must not alter operational values.

Current optimizer objective in `be/app/inventory/optimization.py` minimizes total 72-hour shortage weighted by broad risk level, then purchase cost. It does not model daily inventory balance or arrival timing inside the objective.

## XGBoost audit

Dataset:

- `be/data/new_data/aruna_juice.csv`
- 4,015 synthetic product-day rows, 11 products.
- Dataset SHA-256: `f6461f8934d5a879c0bdc0fbd07d4dbbac9209139ce03e65637c4f0f9561cac0`
- Artifact version: `juice-xgb-direct-v1`

Temporal splits:

| Split | Rows | Period |
| --- | ---: | --- |
| Train | 2,552 | 2025-09-29 to 2026-05-18 |
| Validation | 528 | 2026-05-22 to 2026-07-08 |
| Test | 528 | 2026-07-12 to 2026-08-28 |

Leakage audit passed:

- Zero duplicate date/product rows.
- Zero active-split missing features or targets.
- Targets excluded from feature pipelines.
- Preprocessing fitted on train only.
- Splits are temporally ordered with D+3 embargo.
- Zero lag mismatches.
- Zero D+1/D+2/D+3 target mismatches.
- Rolling features include only completed day `t` and prior history.

Official MAE:

| Horizon | Validation XGB | Validation persistence | Test XGB | Test persistence |
| --- | ---: | ---: | ---: | ---: |
| D+1 | 2.8915 | 3.9299 | 2.9934 | 4.2159 |
| D+2 | 2.9043 | 4.2689 | 3.0130 | 4.3371 |
| D+3 | 2.9102 | 4.0436 | 3.0323 | 4.0303 |

Test-set supplemental metrics:

| Horizon | RMSE | WAPE | R2 | Mean prediction error |
| --- | ---: | ---: | ---: | ---: |
| D+1 | 3.9285 | 25.42% | 0.6376 | -0.3939 |
| D+2 | 3.9383 | 25.57% | 0.6360 | -0.4945 |
| D+3 | 3.9736 | 25.82% | 0.6209 | -0.4320 |

The model beats persistence on all recorded validation/test comparisons. It remains synthetic-only, uses one temporal split, lacks prediction intervals, and has already exposed test results. Do not tune Iter2 hyperparameters against test metrics. Model selection must use validation only, followed by one frozen test run.

## Heavy-case root cause

I03 heavy uses:

- 425 cups actual demand.
- 2 kg initial stock per ingredient.
- IDR 500,000 shared budget.
- 15 kg storage per ingredient.
- Fast offer: 1 kg pack, MOQ 2, capacity 10, IDR 30,000, 24 hours.
- Slow offer: 5 kg pack, MOQ 1, capacity 2, IDR 80,000, 48 hours.

Current Iter1 purchases six slow 5 kg packs for IDR 480,000. The selected ingredients are `ING-001`, `ING-002`, `ING-003`, `ING-006`, `ING-008`, and `ING-010`. All purchases arrive on day 2 under simulator semantics.

Physical upper bound:

- Initial stock: 22 kg = 88 cups.
- Maximum affordable slow supply: 30 kg = 120 cups.
- Oracle maximum: 208 / 425 cups = 48.941176% Service Level.
- Iter1: 186 / 425 = 43.764706%.
- Iter1 achieves 89.42% of the scenario oracle and has 22 cups of service regret.

Heavy forecast:

- Predicted total: 363 cups.
- Actual total: 425 cups.
- Underforecast: 62 cups or 14.59%.
- MAE: 2.909091 cups/product-day.
- RMSE: 4.327502 cups/product-day.

Budget is the main binding constraint. Forecast quality matters for allocation, but cannot raise raw heavy Service Level above the 48.94% physical ceiling.

## Prototype finding for Iter2

A read-only time-indexed CP-SAT prototype used the same XGBoost forecast and frozen testcase. It maximized predicted daily fulfilled value minus purchase cost while respecting budget, MOQ, capacity, storage, and arrivals.

| Metric | Iter1 | Prototype | Oracle |
| --- | ---: | ---: | ---: |
| Fulfilled | 186 | 205 | 208 |
| Service Level | 43.764706% | 48.235294% | 48.941176% |
| Unfulfilled | 239 | 220 | 217 |
| Operational cost | IDR 5,260,000 | IDR 4,880,000 | about IDR 4,820,000 |
| Feasible fulfillment | 89.42% | 98.56% | 100% |

Potential improvement without changing the scenario:

- +19 fulfilled cups.
- +4.470588 Service Level percentage points.
- -19 unfulfilled cups.
- -IDR 380,000 operational cost.

## Recommended Iter2 work

### I2.1 Time-indexed procurement model

Implement in production code, not only the evaluator:

- Add daily required quantities to the optimizer input from the risk engine.
- Add daily inventory balance per ingredient.
- Credit each supplier offer only on its actual arrival day.
- Add daily served-demand and shortage variables.
- Enforce storage capacity on the arrival day after prior consumption.
- Preserve budget, MOQ, pack size, supplier capacity, and integer quantities as hard constraints.
- Preserve response contracts and deterministic solver settings.

Use lexicographic priorities:

1. Minimize daily stockout/lost-sales cost.
2. Minimize ending safety-stock deficit.
3. Minimize purchase cost.

Prefer sequential optimization passes or carefully proven objective bounds over arbitrary large weights.

### I2.2 Granular risk priority

All heavy-case ingredients currently become `HIGH`. Add deterministic priority inputs based on:

- First stockout day.
- Daily shortfall magnitude.
- D+1 demand.
- Lost-sales value.
- Forecast uncertainty.

Keep public risk enums stable unless the FE contract is versioned.

### I2.3 Evaluation-only oracle metrics

Add without feeding ground truth to the decision system:

- `feasibleFulfillmentPercent = systemFulfilled / oracleMaximumFulfilled * 100`
- `serviceRegretUnits = oracleMaximumFulfilled - systemFulfilled`
- `operationalCostRegret = systemCost - oracleMinimumCost`

The oracle runs after system decisions and is diagnostic only.

### I2.4 Forecast work after optimizer

- Do not replace XGBoost first; the heavy-case forecast-based prototype is only three cups below the oracle.
- Add validation-derived uncertainty buffers or quantile models later.
- Use rolling-origin validation if time permits.
- Never tune on the frozen test cases or regenerate data for a better score.

### I2.5 Qwen boundary

Do not replace the deterministic risk engine or solver with Qwen. System prompts are not hard constraints. Qwen may propose bounded policy parameters or explain results, but Pydantic validation, deterministic recalculation, solver feasibility, and constraint checks remain authoritative.

Alternative solver benchmark: SciPy `milp`/HiGHS can express the same time-indexed MILP. Changing solver without changing formulation is not expected to improve KPI. Keep OR-Tools for the first Iter2 implementation and use HiGHS only as an independent benchmark if useful.

## Verification commands

From repository root:

```powershell
.\be\.venv\Scripts\ruff.exe check be eval
.\be\.venv\Scripts\python.exe -m compileall -q be\app eval
.\be\.venv\Scripts\pytest.exe be\tests\test_inventory_product_track.py -q
.\be\.venv\Scripts\python.exe -m eval.suite --label iter2
```

After generating a frozen Iter2 artifact:

```powershell
.\be\.venv\Scripts\python.exe -m eval.bridge `
  --legacy eval\results\baseline_20260926_111142.json `
  --inventory eval\results\<iter2-artifact>.json
```

Do not run or modify the legacy suite merely to improve its baseline. Compare Iter1 to Iter2 using identical inventory cases, actual demand, metric formulas, and simulator.

## Required reporting language

Safe current conclusion:

> Iter1 demonstrates end-to-end inventory forecasting and constraint-safe procurement. It performs perfectly in the normal case and fails truthfully in the impossible case. Under heavy constraints it reaches 89.42% of the physical fulfillment ceiling, while a time-indexed prototype indicates a path to 98.56%. Cross-domain superiority over legacy ARUNA is not yet proven.

Do not claim that Iter1 already beats legacy ARUNA operationally until both systems run a genuinely shared decision problem or the claim is explicitly limited to normalized contextual evidence.
