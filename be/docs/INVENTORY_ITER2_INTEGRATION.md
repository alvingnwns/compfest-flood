# Inventory Iteration 2 integration

Backend-only port from upstream commit `22179af`, onto the local integration-hardening worktree.
This is not a Git merge: branch history, checkpoint artifacts, evaluation code/results and frontend presentation are unchanged.

## Imported behavior

- Daily D+1..D+3 stock balances and actual WIB supplier arrival dates.
- Sequential objectives: service/lost-sales value, urgency, ending safety stock, purchase cost.
- Internal deterministic ingredient priority, including validation-split MAE as an uncertainty tie-break; no training, tuning or artifact changes.
- Arrival-dated approved commitments for duplicate-order avoidance only. They remain unconfirmed and never change physical stock or public risk inbound.
- Optimizer version in the plan-cache fingerprint, and urgency ordering of persisted recommendations.

## Local invariants retained

- At most one supplier offer per ingredient per plan, matching the existing `UNIQUE(plan_id, ingredient_id)` constraint. Insufficient supplier capacity is a truthful PARTIAL plan. No schema migration or split-order support was introduced.
- Adapted optimizer version: `time-indexed-lexicographic-v2-single-offer`. Upstream Iteration 2 evaluation scores are not evidence for this stricter formulation; no evaluation was rerun.
- Approved outstanding recommendations remain accessible across newer plans, retaining original recommendation/plan/supplier IDs and received/outstanding quantities.
- Physical receiving stays idempotent and approval alone does not increase stock.
- Numeric inventory-version snapshots and stale stocktaking guards remain.
- Canonical BOM validation, checkout retry/idempotency and independent training/runtime/history provenance remain.
- Public endpoint paths, risk enums and frontend-facing response fields remain compatible; no UI rewrite is required.

Reference: `be/INVENTORY_BACKEND_CONTRACT.md` is the user's upstream contract copy. It describes Iteration 2 generally; the single-offer adaptation and receiving/version/provenance additions above are local compatibility requirements.

## Verification isolation

Backend regressions use a disposable PostgreSQL database named `aruna_hardening` on a host named `aruna-hardening-db-*`. Tests refuse other database targets. Test containers do not receive the application's env file or demo credentials.
Coverage includes arrival timing, budget/storage/MOQ, daily balances, deterministic priority, single-offer persistence, completed sale/BOM deductions, duplicate sale/receiving replay, receiving across plans, stale stocktaking, Qwen timeout and forecast provenance.

Verification result: 41 backend tests passed against the disposable PostgreSQL instance; scoped backend Ruff checks passed. Existing frontend suite: 173 passed, 2 intentionally skipped live smoke tests; typecheck and lint passed.

Deployment completed after space was freed on Windows drive C: and Docker Desktop was restarted. The earlier dependency-download I/O failure was resolved; the production backend image built successfully, and backend plus frontend are healthy.

Post-build runtime verification confirmed the single-offer optimizer version, a PARTIAL multi-offer probe with exactly one selected offer, successful loading of all three existing forecast artifacts, and public JSON fields `inventoryVersion`, `trainingDataSynthetic`, `outstandingRecommendations`. These checks did not access a database. Backend health and landing plus all seven active inventory UI HTML routes returned HTTP 200.

Targeted cleanup removed only temporary containers `aruna-hardening-db-iter2`, `aruna-hardening-tests-iter2`, `aruna-hardening-tests-iter2-final`, the disposable PostgreSQL volume, and network `aruna-hardening-net-iter2`. Disposable test records were not retained. No broad Docker cleanup, demo-database mutation, training, evaluation or Git-history change was performed.
