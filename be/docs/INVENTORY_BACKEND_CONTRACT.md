# ARUNA Inventory Backend Contract

Status: backend implementation contract aligned to FE–BE Source of Truth v1.1

Scope: Product Track inventory and procurement APIs under `/api`

Timezone: API timestamps are UTC; business dates and month boundaries use `Asia/Jakarta`

Persistence: PostgreSQL through Supabase, isolated in the `aruna_inventory` schema

This contract does not change the preliminary flood recovery API or evaluation semantics. Examples describe shapes, not seeded values.

## Ownership and pipeline

```text
POS transaction
  -> persisted sale and inventory ledger
  -> XGBoost product forecast D+1/D+2/D+3
  -> deterministic BOM conversion
  -> deterministic Inventory Risk Engine
  -> OR-Tools procurement optimization
  -> Pydantic-validated structured decision context
  -> Qwen explanation or deterministic fallback
  -> owner decision
  -> physical receiving
```

- XGBoost predicts product demand only.
- BOM conversion produces ingredient requirements.
- Risk rules produce risk level, projections, and reason codes.
- OR-Tools produces recommended quantities, supplier selection, cost, ETA, solver status, and unmet need.
- Qwen explains the immutable structured result. Its output cannot alter operational values.
- Approval records an owner decision. It does not place an external order or change stock.
- Receiving changes stock exactly once through the ledger.

## General conventions

### JSON and IDs

- Request and response fields use `camelCase`.
- IDs are opaque strings.
- Money is integer IDR with `currency: "IDR"`.
- Missing domain values use JSON `null`, not an empty string.

### Time

- Persisted instants use `timestamptz` and API timestamps use ISO 8601 UTC with `Z`.
- `date`, daily sales aggregation, completed forecast day, and monthly activity-log partition boundaries use `Asia/Jakarta`.
- Forecast dates use `YYYY-MM-DD`.
- Server timezone does not determine business dates.

### Units and precision

Supported API units are `g | kg | ml | l | pcs`.

Each ingredient has one configured API display unit and one normalized integer storage scale:

| Kind | Stored unit | API conversion |
| --- | --- | --- |
| Weight | milligram | `g = mg / 1000`, `kg = mg / 1000000` |
| Volume | microlitre | `ml = µl / 1000`, `l = µl / 1000000` |
| Discrete | piece | `pcs` remains integer |

All quantities concerning the same ingredient in one response use that ingredient's API unit. API inputs must convert exactly to the storage scale. Product quantities and `pcs` must be integers. Intermediate supplier cost uses integer arithmetic at the normalized pack level; final amounts are integer IDR.

### Errors

New inventory endpoints use this envelope:

```json
{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "Inventory could not be updated.",
    "details": null
  }
}
```

Expected statuses are `201` for creation, `200` for reads/decisions, `422` for schema/domain validation, `404` for missing resources, `409` for state conflicts, `503` for unavailable database/configuration, and `500` for unexpected failures. Inventory validation errors use the same envelope. Existing preliminary endpoints retain their current error envelope.

Canonical conflict codes include `INSUFFICIENT_INVENTORY`, `IDEMPOTENCY_CONFLICT`, `STALE_INVENTORY`, `STALE_RECOMMENDATION`, `DECISION_CONFLICT`, `DUPLICATE_RECEIPT`, `OVER_RECEIPT`, `FORECAST_UNAVAILABLE`, and `MISSING_PROCUREMENT_CONSTRAINT`.

### Idempotency

`POST /api/transactions`, inventory adjustments, and stock-in accept an optional `Idempotency-Key` header.

- Same key and canonical payload returns the original successful response.
- Same key with a different payload returns `409 IDEMPOTENCY_CONFLICT`.
- Missing key is accepted and creates a new mutation.
- CORS permits `Idempotency-Key`.

## Canonical entities

### Product

```json
{
  "id": "prod_strawberry",
  "name": "Jus Stroberi",
  "price": 20000,
  "currency": "IDR",
  "isActive": true
}
```

### Ingredient and recipe

```json
{
  "id": "ing_strawberry",
  "name": "Stroberi",
  "category": "Buah",
  "unit": "kg",
  "currentStock": 8.2
}
```

```json
{
  "productId": "prod_strawberry",
  "ingredientId": "ing_strawberry",
  "quantityRequired": 0.2,
  "unit": "kg"
}
```

### Supplier and offer

Supplier fields are `id`, `name`, `leadTimeHours`, and `isActive`. An offer adds `supplierId`, `ingredientId`, `unit`, `unitCost`, `minOrderQuantity`, and `capacity`. Unknown optional constraints are `null`; a required missing constraint produces a domain error rather than being interpreted as zero or unlimited.

## Endpoint matrix

### `GET /api/products`

Returns `{ "products": Product[] }` for POS and product selectors.

### `POST /api/transactions`

Request:

```json
{
  "source": "POS_SIMULATOR",
  "items": [{ "productId": "prod_strawberry", "quantity": 2 }]
}
```

`source` is `POS_SIMULATOR | POS_CASHIER | IMPORT`. Quantity is a positive integer. The database transaction validates active products, complete BOM, and sufficient stock; persists the sale and items; records normalized ingredient movements; increments inventory version; and records the success activity event. Failure commits none of those changes.

Response `201`:

```json
{
  "transaction": {
    "id": "txn_001",
    "createdAt": "2026-09-26T04:30:00Z",
    "source": "POS_SIMULATOR",
    "currency": "IDR",
    "totalAmount": 40000,
    "totalItems": 2,
    "items": [
      {
        "productId": "prod_strawberry",
        "productName": "Jus Stroberi",
        "quantity": 2,
        "unitPrice": 20000,
        "subtotal": 40000
      }
    ],
    "ingredientConsumption": [
      {
        "ingredientId": "ing_strawberry",
        "ingredientName": "Stroberi",
        "quantity": 0.4,
        "unit": "kg"
      }
    ]
  }
}
```

### `GET /api/transactions`

Queries: `search`, `date`, `page=1`, `pageSize=20`. Returns summary `items` and `{ page, pageSize, totalItems, totalPages }` pagination.

### `GET /api/transactions/{transactionId}`

Returns the same detailed `transaction` shape as checkout. Ingredient consumption comes from persisted backend movements/BOM processing.

### `GET /api/inventory`

Queries: `search`, `riskLevel`. Returns `{ items: InventoryItem[] }`. Each item includes:

- `ingredientId`, `ingredientName`, `category`, `unit`, `currentStock`, `updatedAt`;
- `predictedRequirement`, `requirementHorizonDays`, `riskLevel`, and `riskReason` from the current canonical snapshot.

Risk level is `LOW | MEDIUM | HIGH | STOCKOUT`.

### `GET /api/inventory/movements`

Queries: `ingredientId`, `type`, `page=1`, `pageSize=20`. Movement type is `SALE | STOCK_IN | ADJUSTMENT | WASTE | DAMAGE`. Returns signed `quantityChange`, explicit `unit`, nullable `transactionId` and `note`, UTC `createdAt`, and pagination.

### `POST /api/inventory/{ingredientId}/adjustments`

Request fields:

- `countedStock`: nonnegative absolute physical count;
- `unit`: must match the ingredient unit;
- `reason`: `PHYSICAL_COUNT | WASTE | DAMAGE | OTHER`;
- `note`: nullable text;
- `expectedInventoryVersion`: optional optimistic guard.

The operation locks the ingredient, reads current stock, computes the delta, records the appropriate movement and activity event, increments inventory version, and returns `{ inventory, movement }`. WASTE/DAMAGE cannot increase stock. A zero delta returns `movement: null` only after the FE accepts that additive schema; until then the implementation returns an explicit compatible movement object.

### `POST /api/inventory/{ingredientId}/stock-in`

Request fields are `quantity`, `unit`, `supplierId`, nullable `note`, optional `recommendationId`, and optional `externalReceiptId`. It returns `{ inventory, movementId }`.

With a recommendation, the ingredient and supplier must match, the decision must be approved, partial receiving is permitted, and quantity cannot exceed the outstanding amount. A unique external receipt prevents duplicate stock. Without a recommendation it is an unlinked manual receipt and does not change recommendation lifecycle by inference.

### `GET /api/forecasts/products/{productId}?horizonDays=3`

Only `horizonDays=3` is accepted. Response contains:

- product identity;
- `generatedAt`, `horizonDays`, and honest model name/version;
- completed-day history with `actualDemand` and optional `historySource`;
- D+1/D+2/D+3 `forecast` entries;
- deterministic BOM `ingredientRequirements` for this product;
- optional run ID, `asOfDate`, cutoff, `source`, synthetic flag, and fallback reason.

At intraday request time, the origin is the latest completed WIB calendar day. Training never runs in the request. Observed API sales are fulfilled sales and may be stockout-censored; the supplied training target is synthetic unconstrained demand. A fallback must be labeled `FALLBACK`. If no defensible forecast exists, return `409 FORECAST_UNAVAILABLE`.

### `GET /api/inventory/risks`

Optional query: `level`. Returns `generatedAt`, `horizonDays: 3`, and items containing ingredient identity/unit, current and incoming stock, predicted requirement, ending projected stock, safety stock, reorder point, lead time, level, and human-readable rule reason.

Risk precedence:

1. `STOCKOUT`: usable current stock is zero and forecast requirement is positive.
2. `HIGH`: positive current stock becomes negative during the horizon, or demand cannot be covered before eligible replenishment.
3. `MEDIUM`: no higher rule applies and projected stock falls below safety stock.
4. `LOW`: none apply.

Zero stock and zero requirement is not `STOCKOUT`. Confirmed physical inbound is credited only on its eligible arrival date. Approval is not inbound. Optional metadata may expose reason codes, projected stockout date, inventory version, forecast run ID, and daily projection.

### `GET /api/procurement/recommendations`

The backend reuses a persisted nonstale plan for identical inventory, forecast, supplier/constraint versions, and budget. Otherwise it runs the bounded OR-Tools model. It never auto-approves, purchases, or receives goods.

Response required fields are `generatedAt`, `optimizerStatus`, and `recommendations`. `optimizerStatus` is `OPTIMAL | FEASIBLE | INFEASIBLE | ERROR`. Each recommendation contains ingredient, unit, stock/requirement/safety/projection, risk, recommended order quantity/date, supplier, `PENDING | APPROVED | REJECTED` status, and explanation `{ text, source }`, where source is `QWEN | FALLBACK`.

Optional plan metadata includes plan ID, input versions, staleness, `COMPLETE | PARTIAL | INFEASIBLE` outcome, solver detail, total integer IDR cost, limitations, line ETA/cost/reason codes, and unmet quantity. A solver optimum may still be partial when the modeled objective permits shortage with penalty.

The model enforces configured shared budget, pack/MOQ, lead time, supplier capacity, and storage capacity. Approved outstanding quantities reserve decision budget but remain unconfirmed and do not count as stock or inbound.

### `POST /api/procurement/recommendations/{recommendationId}/decision`

Request: `{ "decision": "APPROVED" }` or `REJECTED`. Response contains `id`, final `status`, and UTC `reviewedAt`.

- Repeating the same decision is idempotent.
- An opposite final decision returns `409 DECISION_CONFLICT`.
- A recommendation created from older inventory/forecast/constraint versions returns `409 STALE_RECOMMENDATION`.
- Approval never changes physical stock.

### `GET /api/dashboard/summary`

Returns UTC `generatedAt`; today's WIB revenue, transaction count, and products sold; at-risk ingredient and active recommendation counts; and priority actions. Values derive from the same sales, forecast, inventory, risk, and recommendation snapshots used by their canonical endpoints.

## Forecast artifact contract

The official phase dataset is `be/data/new_data/aruna_juice.csv`. It is synthetic POS-like demand shaped for a target juice business and is not evidence of real-world accuracy or business impact.

Artifact directory defaults to `be/artifacts/inventory/` and contains three direct-horizon pipelines plus a manifest. Every pipeline includes product encoding and numeric preprocessing fitted only on `train`. Features are exactly:

```text
product_id
demand_cups_t
lag_1 lag_2 lag_3 lag_7 lag_14 lag_28
rolling_mean_7 rolling_mean_14 rolling_mean_28
rolling_std_7 rolling_std_14
```

All three target columns and metadata are excluded from model features. `warmup`, `embargo`, and `inference_only` are excluded from fitting. Validation/test remain untouched and each horizon is compared with a documented simple baseline.

## Activity log contract

Inventory-domain successful mutations and activity events commit atomically. Events cover checkout, void, stocktake, receiving, forecast generation, plan generation, approval, and rejection. Each record includes action, entity, source/actor where known, correlation ID, UTC timestamp, WIB business date/month, and sanitized JSON metadata. Credentials and tokens are forbidden.

Activity logs are range-partitioned by WIB month. Migration prepares the current and following month, and runtime safely prepares a needed partition before insertion. Failed attempts use a separate transaction so they remain visible after the business transaction rolls back.

## Qwen structured explanation contract

The context sent to Qwen is a Pydantic-validated object containing plan and snapshot IDs, model/source metadata, three-day forecast, BOM-derived requirements, daily risk projections and reason codes, solver status/outcome, recommendations, supplier/ETA/cost, unmet quantities, and limitations.

Qwen returns schema-constrained `{ summary, recommendationExplanations[] }`. Recommendation IDs must match the supplied context. The backend returns operational numbers from the stored OR-Tools result, never from Qwen output. Missing credentials, timeout, provider error, invalid JSON/schema, unknown ID, or numerical inconsistency selects deterministic fallback text without invalidating the plan.

## Cache invalidation expectations

- Checkout: transactions, transaction detail, inventory, movements, dashboard, risk, and recommendations.
- Adjustment/stock-in: inventory, movements, risks, recommendations, and dashboard.
- Recommendation decision: recommendations and dashboard.
- A transaction does not retrain the model. Inventory mutations make pending plans stale; forecast lifecycle is independently versioned.
