# Inventory frontend integration

The seven ARUNA inventory pages use the backend when NEXT_PUBLIC_DATA_SOURCE=api (default). Explicit mock mode is retained for isolated tests and offline development. API failures are shown, never silently replaced with mock data.

Pipeline: inventory-api Zod response contracts → services/adapters → TanStack Query hooks → presentation.

- Backend Docker reads be/.env, including INVENTORY_DATABASE_URL. No credentials enter the frontend build.
- POS uses GET /api/products and POST /api/transactions. The service supplies the internal POS_SIMULATOR origin; transaction source is not displayed.
- Sales reads today's WIB paginated transactions and fetches selected details on demand.
- Inventory reads stocks, risks and paginated movements; stocktaking and physical receiving use idempotency keys.
- Forecast uses real product IDs and three-day forecast entries. Backend BOM totals remain in the service contract, but the standalone totals block is omitted from the page. A compact expandable explanation preserves synthetic-training and fallback provenance without raw model versions or reason codes. The chart supports forward, backward and combined ranges, anchored on the backend's first forecast date; missing historical values are not fabricated.
- Risk statuses distinguish HIGH (projected shortage) from STOCKOUT (zero stock). Expiry and surplus are not inferred from this API.
- Procurement displays suppliers and recommendation cost, and supports APPROVED/REJECTED decisions. Raw solver status and diagnostic codes are not displayed; infeasible and partial plans retain plain-language warnings. Approval does not increase stock. Approved recommendations can be physically received through the stock-in endpoint.
- Successful mutations invalidate all inventory query families, leaving legacy simulation queries untouched.
- Backend does not expose product recipes in the catalogue or standalone supplier/lot endpoints. POS omits unknown recipe usage; manual receiving offers suppliers found in procurement recommendations, with explicit supplier-ID entry when none are exposed.
- Importing sales has no supported endpoint; the UI does not advertise an import action.

Verification: npm run typecheck; npm run lint; npm run test; Docker production build.
Optional live adapter check: set ARUNA_API_SMOKE=1 and run src/services/inventory-live.test.ts against localhost:8000. It makes no sale, approval, adjustment or receiving mutations.

Optional transaction check: also set ARUNA_API_MUTATION_SMOKE=1. This creates one real sale, verifies idempotent checkout, Sales details and inventory deductions, then voids that test transaction and verifies stock restoration. The transaction and reversal remain in the audit trail; this is not a read-only check.

## Integration hardening

- Checkout validates **all persisted canonical BOM dependencies**, including inactive ingredients and inconsistent unit/scale definitions, before recording any sale or ledger deduction. Water/ice/sugar are not inferred as dependencies. Missing canonical rows cannot be inferred without a separately maintained recipe definition; the current database recipe remains the source of truth.
- Procurement responses include `outstandingRecommendations` across plans and canonical `planId`, `receivedQuantity`, `outstandingQuantity`. The frontend merges by recommendation ID and keeps old approved commitments in the Approved tab until fully received. Receiving retains the original recommendation ID and supplier. Approval alone changes no stock.
- An uncertain POS result locks cart editing and offers **Retry same order**, reusing the captured payload and idempotency key. Definitive domain errors offer Back to Order. Recovery currently lives in the mounted page: do not reload/navigate away while resolving an uncertain result; durable cross-reload recovery is not implemented.
- `GET /api/inventory` returns numeric `inventoryVersion` associated with the balance snapshot. Stocktaking freezes that version when opened and sends `expectedInventoryVersion`. A stale conflict invalidates inventory queries and blocks resubmission until the form is closed and stock is recounted. Missing version disables adjustments rather than bypassing the guard. Direct API callers must also supply the existing optional version guard.
- Solver selects at most one supplier offer per ingredient to match the existing per-plan persistence constraint. If one offer cannot cover demand, unmet demand remains a truthful PARTIAL outcome. Splitting orders across suppliers is deliberately unsupported.
- Ingredient, risk, quantity, supplier, order date and cost come from structured fields. Qwen/FALLBACK prose is labelled explanation-only; provider timeout preserves deterministic recommendations. No new LLM validation framework is added, so prose itself can still be inaccurate.
- Forecast response adds `trainingDataSynthetic` read from the existing manifest. This is separate from runtime `source` (XGBOOST/FALLBACK), `isSynthetic`, `fallbackReason`, and per-point `historySource` (OBSERVED_SALES/SYNTHETIC_DEMAND). Forecast and overview UI preserve these distinctions; synthetic history is not labelled actual sales. No training, tuning, or artifact changes were made.

### Safe verification

Normal frontend tests must not enable ARUNA_API_SMOKE or ARUNA_API_MUTATION_SMOKE against the shared demo database. Even forecast/procurement GETs can persist cached runs/plans. No shared-database smoke or concurrency test was run during hardening.

`be/tests/test_inventory_hardening.py` runs real PostgreSQL regressions only when ARUNA_TEST_DATABASE_URL points to database `aruna_hardening` on a host named `aruna-hardening-db-*`. It resets only that disposable schema, refusing other targets. The suite covers invalid partial BOM, missing BOM/demo recipe scope, duplicate sale retry, full sale-to-receiving trace across plans, stale stocktaking, multi-offer solver/persistence, Qwen timeout and forecast provenance. Without this isolated database it skips mutation tests.

Final checks: frontend typecheck/lint/134 normal tests/production build; backend 25 relevant tests including 11 hardening cases. Shared live smoke tests remain disabled. The endpoint matrix test uses public OpenAPI paths rather than FastAPI internal router objects.

Isolated final trace: sell 2 cups of P009 for Rp 40,000; canonical BOM deducts 0.5 kg strawberry; one sale/SALE movement despite same-key replay; stock 10 → 9.5 kg. FALLBACK forecast gives 51 cups/12.75 kg requirement and HIGH risk. Solver recommends 10 kg. Approval leaves 9.5 kg unchanged. Receive 2.5 kg once despite receipt replay → stock 12 kg. A newer plan still exposes the original approved recommendation with 7.5 kg outstanding and unchanged supplier/plan relationship. Final 7.5 kg receiving → stock 19.5 kg; outstanding entry disappears and exactly two receiving movements retain the original recommendation link.

### Files changed by hardening

- Backend runtime: `be/app/inventory/{operations,procurement,risk,optimization,forecast,schemas}.py`.
- Backend tests: `be/tests/test_inventory_hardening.py` (new), `be/tests/test_inventory_product_track.py` (endpoint registration assertion only).
- Frontend contracts: `fe/src/domain/{inventory-api,inventory,optimization-plan,demand-forecast,dashboard}.ts`.
- Frontend services: `fe/src/services/{inventory-service,optimization-plan-service,demand-forecast-service,dashboard-service}.ts`; updated `inventory-api-integration.test.ts`.
- POS: `fe/src/features/pos-simulator/{pos-simulator-page,pos-dialog}.tsx`; new `pos-retry.test.tsx`.
- Stocktaking: `fe/src/features/inventory/stock-mutation-form.tsx`; new `stock-mutation-form.test.tsx`.
- Procurement UI: `fe/src/features/optimization-plan/optimization-plan-page.tsx`; new `optimization-integration.test.tsx`.
- Forecast UI: `fe/src/features/demand-forecast/{demand-forecast-page,forecast-chart}.tsx`; new `forecast-provenance.test.tsx`.
- Overview UI: `fe/src/features/dashboard/{dashboard-page,demand-projection-chart}.tsx`.
- Documentation: this file. Next.js production build automatically updates generated `fe/next-env.d.ts` to production type paths.

Pre-existing landing, shell, compose, legacy and other worktree edits were preserved. No Git commits/tags/history, model artifacts, baseline, training or evaluation infrastructure changes were made.

## Inventory UI empty and loading states

- The seven active inventory pages reuse `components/inventory/inventory-page-state.tsx` for localized empty, loading and retryable error states. Illustration assets in `public/inventory-states` are exports of the referenced ARUNA Figma empty-state components, scaled for the compact application shell.
- Empty states require successfully loaded empty datasets. Errors remain errors; API failures never trigger mock fallback. Search/status filters with no matches retain their existing table headers and inline messages.
- A successfully returned empty product catalogue has a validated empty forecast service result, with no invented product identifier and no forecast endpoint call. Zero-valued forecasts, safe stock, a populated catalogue with an empty basket, and days without sales but with inventory are not treated as missing data.
- Optimization retains plain-language infeasible/partial warnings without raw solver status or diagnostic codes. Overview uses an explicit inventory-presence flag from the service rather than interpreting a zero risk count as absent inventory. Its Pending Actions table scrolls inside a bounded desktop grid, with sticky headers and a keyboard-focusable scroll region; the technical chart footer and raw material risk prose are omitted.
- Calls to action use existing POS/inventory routes or the inventory stock tab. Unsupported import/catalogue-creation actions are not advertised. No new production mock, backend endpoint or database mutation was added.
- Regression fixtures are isolated behind services in tests. Shared-database API and mutation smoke tests remain disabled.
