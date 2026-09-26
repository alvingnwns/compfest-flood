# ARUNA backend rework checklist

Branch: `dev/phase2`

Scope: `be/` only

Contract: `C:\Downloads\ARUNA_FE_BE_SOURCE_OF_TRUTH_v1.1.md`

Status: `[x]` verified; `[ ]` still needs external input or follow-up.

## Confirmed direction

- [x] Python, FastAPI, Pydantic, PostgreSQL via Supabase.
- [x] XGBoost direct D+1/D+2/D+3 forecast.
- [x] Deterministic Inventory Risk Engine.
- [x] Google OR-Tools procurement optimizer.
- [x] Qwen explains structured forecast, risk, and optimizer output only.
- [x] Secrets remain environment supplied and absent from source/output.

## B0 — Audit and contract alignment

- [x] Audit branch, Git status, backend structure, dependencies, and existing API.
- [x] Confirm work began before the 26 September 2026 20:00 WIB freeze.
- [x] Confirm `data/new_data/aruna_juice.csv` as authorized synthetic POS-like training data.
- [x] Document exact v1.1 endpoints, fields, enums, errors, units, money, and time conventions.
- [x] Reconcile the implementation to canonical URLs, envelopes, prices, source, supplier, units, and UTC timestamps.
- [ ] Compare against FE Zod schemas/services when the FE product pages exist. No matching product endpoint integration was present during this backend-only phase.

## B1 — PostgreSQL persistence and audit

- [x] Create and run the isolated `aruna_inventory` schema migration without changing prior public draft tables.
- [x] Persist products, ingredients, recipes, suppliers/offers, sales/items, ledger, forecasts, plans, recommendations, receipts, idempotency, and activity logs.
- [x] Store integer IDR and normalized integer quantity bases; preserve fractional API units and integer `pcs`.
- [x] Use atomic transactions and ordered row locks to prevent partial checkout and concurrent overselling.
- [x] Keep stock ledger backed and versioned; separate decisions from physical receipts.
- [x] Partition activity logs by WIB month and record sanitized success/failure activity.
- [x] Seed 11 menus with explicitly documented demo assumptions.
- [x] Verify persistence across separate migration, seed, API, and verification processes.

## B2 — FE-compatible POS and inventory

- [x] `GET /api/products`.
- [x] Atomic `POST /api/transactions`, with optional `Idempotency-Key`.
- [x] Transaction search/date/pagination and detail endpoints.
- [x] Documented transaction void/reversal extension.
- [x] Inventory list and paginated movement ledger.
- [x] Unit-safe, version-aware stock adjustment with WASTE/DAMAGE direction rules.
- [x] Manual and linked partial receiving, receipt deduplication, and over-receipt protection.
- [x] Canonical inventory error envelope; existing recovery error behavior retained.

## B3 — Three-day demand forecast

- [x] Document dataset provenance, generator, split semantics, features, and limitations.
- [x] Train direct D+1/D+2/D+3 XGBoost pipelines using train rows only.
- [x] Evaluate validation/test against persistence baseline and record all metrics.
- [x] Persist models, preprocessing, feature contract, cutoff, hash, versions, and metrics.
- [x] Infer from completed WIB days; distinguish fulfilled runtime sales from synthetic demand.
- [x] Return product forecast, history/source metadata, and BOM-derived ingredient requirements.
- [x] Use an explicitly labeled fallback for insufficient observed history; never train during requests.

## B4 — Inventory risk

- [x] Use persisted forecast, BOM, inventory, and version data consistently.
- [x] Aggregate every active product contribution to shared ingredients.
- [x] Project stock daily and credit only physically confirmed eligible incoming stock.
- [x] Apply `STOCKOUT > HIGH > MEDIUM > LOW` precedence, including lead-time shortage.
- [x] Return risk reason codes, quantities, units, reorder point, lead time, horizon, and limitations.

## B5 — Procurement and owner decision

- [x] Optimize shared budget, pack/MOQ, lead time, supplier capacity, storage, cost, and shortage with CP-SAT.
- [x] Persist stable versioned plans and reuse the same current plan under repeated/concurrent reads.
- [x] Expose truthful solver status, plan outcome, unmet quantity, costs, ETA, and limitations.
- [x] Handle idempotent owner decisions, opposite-decision conflict, and stale recommendation conflict.
- [x] Reserve approved outstanding budget without treating approval as stock or an external purchase.

## B6 — Qwen explanation

- [x] Build inventory-only Pydantic context from persisted forecast, risk, and optimization values.
- [x] Request schema-constrained OpenRouter/Qwen output and validate IDs and shape.
- [x] Prevent Qwen from changing operational values; persist explanation text/source only.
- [x] Support the provider's validated alternate wrapper and deterministic fallback.
- [x] Verify a live Qwen explanation and an offline deterministic fallback.

## B7 — Dashboard, verification, handoff

- [x] Derive dashboard sales, risk count, recommendations, and priorities from persisted data.
- [x] Verify POS → ledger → forecast → risk → recommendation → decision → linked receiving against Supabase PostgreSQL.
- [x] Verify checkout idempotency/conflict, stale plans, decision conflict, partial/duplicate/over receipt, void, and stock restoration.
- [x] Verify two concurrent competing checkouts commit exactly once with no oversell.
- [x] Verify WIB day boundary, monthly activity partitions, forecast metadata, risk precedence, schema validation, and Qwen offline fallback.
- [x] Verify CP-SAT infeasible and timeout/unknown status mapping in isolation; live configured scenario returned `OPTIMAL/COMPLETE`.
- [x] Run Product Track tests: `14 passed`.
- [x] Run lint and compile checks: passed.
- [x] Run full backend regression: `140 passed, 11 failed`; four failures are pre-existing recovery semantics/validation expectations and seven require the absent Dynamic Hazard source ZIP.
- [x] Document setup, migration, seed, model, API/FE mapping, assumptions, and operational limits.
- [x] Recheck time: `2026-09-26 14:01 WIB`, before the 20:00 WIB freeze.

## Review notes

- Supabase migration/seed result: 11 products, 11 ingredients, 11 recipes, 11 offers, 11 opening movements, and monthly audit partitions.
- XGBoost beats persistence on validation and test for all three horizons on this synthetic dataset; no real-world accuracy claim is made.
- Live flow returned Qwen explanations after validating the provider response. Fallback keeps OR-Tools recommendations unchanged.
- Full-suite failures were not changed because they belong to the existing recovery track or an unavailable external dataset, outside this Product Track scope.
