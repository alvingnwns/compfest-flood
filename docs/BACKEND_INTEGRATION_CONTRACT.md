# ARUNA Backend Integration Contract v1.0

Status: frozen for frontend integration. The Zod schemas in `fe/src/domain` are the executable source of truth; this document is the human-readable handoff.

## Architecture Boundary

```text
Next.js pages/components
  -> TanStack Query hooks
  -> scenario/analysis services
  -> shared HTTP client
  -> FastAPI in full-stack mode OR MSW in explicit mock mode
  -> Zod response validation
```

Components never import fixtures or select a data source. FastAPI is the real full-stack implementation; MSW is an explicit development/test implementation of the same contract. JSON uses camelCase, raw numbers, stable entity IDs, ISO-8601 dates/timestamps, and GeoJSON-compatible geometry.

## Environment Configuration

```dotenv
# Optional local mock mode
NEXT_PUBLIC_DATA_SOURCE=mock
NEXT_PUBLIC_API_BASE_URL=

# Current local FastAPI mode
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

In `api` mode the base URL must be a valid absolute URL. Trailing slashes are normalized. MSW starts only in `mock` mode. Because these are Next.js public build-time variables, restart the frontend after changing them.

## API Base URL

All paths below are relative to `NEXT_PUBLIC_API_BASE_URL`. Local development uses frontend `http://localhost:3000` and backend `http://localhost:8000`. FastAPI must allow the frontend origin through CORS, including `GET`, `POST`, `Content-Type`, and `Accept`. Production must use the deployed frontend origin and HTTPS.

## Protocol Conventions

- `eventDate` is an ISO date (`YYYY-MM-DD`). Timestamps are ISO-8601 with timezone/offset, normally UTC `Z`.
- Probabilities and rates are decimal values from `0` to `1`. The frontend formats them as percentages.
- Durations are numeric minutes; distances are numeric kilometres.
- Money is unformatted. The disruption response uses `{ "amount": 8200000, "currency": "IDR" }`; the KPI response uses numeric values plus `currency: "IDR"`.
- Risk values are exactly `low | medium | high | critical`.
- Simulation states are `queued | processing | completed | failed`. Recovery states are `queued | processing | ready | partial | no-feasible-plan | failed`.
- A `201` response may already be complete or may be queued/processing. The frontend polls the corresponding GET resource every second while work is pending. WebSockets are not required.
- Important map geometry is backend-owned. Routes/road risks accept `LineString` or `MultiLineString`; flood extents accept `Polygon` or `MultiPolygon`; facilities use `Point`. Coordinates use GeoJSON order `[longitude, latitude]`.
- No v1 endpoint uses query parameters.

## Failure Response

Every non-2xx response must use:

```json
{
  "code": "simulation_not_found",
  "message": "Simulation not found.",
  "retryable": false,
  "details": { "simulationId": "sim-missing" }
}
```

`details` is optional. Use `400` for malformed request syntax, `404` for missing resources, `409` for a valid request conflicting with resource state, `422` for semantically invalid input, and `500` for unexpected server failures. Set `retryable` deliberately; normally only transient `5xx` failures are retryable. Zod rejects a successful response that does not match the documented schema.

## Endpoint Summary

| Method | Path | Consumer | TanStack operation / key |
| --- | --- | --- | --- |
| GET | `/api/scenarios/historical-jakarta` | Scenario | query `['scenario','historical-jakarta']` |
| POST | `/api/simulations` | Scenario run action | mutation, no cache key |
| GET | `/api/simulations/{simulationId}` | Scenario polling, Simulation Details | query `['simulation', simulationId]`, polls while pending |
| GET | `/api/simulations/{simulationId}/disruption` | Disruption Map | query `['disruption', simulationId]` |
| POST | `/api/simulations/{simulationId}/recovery` | Generate Recovery Plan | mutation, no cache key |
| GET | `/api/simulations/{simulationId}/recovery` | Recovery Plan | query `['recovery', simulationId]`, polls while pending |
| GET | `/api/simulations/{simulationId}/impact` | Impact Analysis | query `['impact', simulationId]` |
| GET | `/api/business-data/template` | Custom data template | direct download |
| POST | `/api/business-data/import` | Custom data validation/import | mutation |
| GET | `/api/business-data/{snapshotId}` | Custom data snapshot preview | query |
| GET | `/api/map/road-context` | Local map road context | query |
| POST | `/api/simulations/{simulationId}/copilot` | ARUNA Copilot | mutation |

Default query policy is one retry, 30-second stale time, and no refetch on window focus.

## Endpoints

### GET /api/scenarios/historical-jakarta

Purpose: return the selectable historical replay and its business network snapshot. Consumer: Scenario page. Path params: none. Query params: none. JSON body: none. Schema: `scenarioSchema` in `fe/src/domain/scenario.ts`.

Response `200`:

```json
{
  "id": "scenario-jakarta-20250304",
  "name": "Jakarta Flood — 04 March 2025",
  "mode": "historical-replay",
  "location": "Jakarta",
  "eventDate": "2025-03-04",
  "eventType": "Urban Flood",
  "dataSources": {
    "mode": "historical_snapshot",
    "historicalStatus": "available",
    "operationalStatus": "simulated",
    "historicalProvider": "local historical archive",
    "snapshotId": "jakarta-2025-03-04-v1"
  },
  "companyName": "Nusantara Foods",
  "facilities": [
    { "id": "sup-a", "name": "Supplier A", "kind": "supplier", "location": { "type": "Point", "coordinates": [106.826, -6.139] } },
    { "id": "wh-east", "name": "Warehouse East", "kind": "warehouse", "location": { "type": "Point", "coordinates": [106.913, -6.229] } }
  ],
  "vehicles": [{ "id": "V-01", "label": "Box Truck 01", "capacityUnits": 800 }],
  "products": [{ "id": "prod-a", "name": "Product A", "unit": "units" }],
  "materials": [{ "id": "mat-a", "name": "Primary Ingredient", "supplierId": "sup-a", "productIds": ["prod-a"] }],
  "inventory": [{ "facilityId": "wh-east", "productId": "prod-a", "quantity": 420, "unit": "units" }],
  "orders": [{ "id": "ORD-008", "storeId": "store-c", "productId": "prod-a", "quantity": 80, "priority": "critical" }]
}
```

Relevant statuses: `200`, `404`, `500`. Historical replay remains valid when live APIs are unavailable: use `mode: historical_snapshot` and `historicalStatus: offline_snapshot` with a local `snapshotId`.

### POST /api/simulations

Purpose: request flood-risk and supply-chain impact analysis for a scenario. Consumer: Scenario run action. Path params: none. Query params: none. Schema: request `runSimulationRequestSchema`; response `simulationSchema`.

Request JSON:

```json
{
  "scenarioId": "scenario-jakarta-20250304",
  "vehicleOverrides": [
    { "id": "V-02", "capacityUnits": 650, "available": true }
  ],
  "customVehicles": [
    {
      "id": "V-04",
      "label": "Kendaraan 04",
      "capacityUnits": 500,
      "available": true
    }
  ],
  "inventoryOverrides": [
    { "facilityId": "wh-west", "productId": "prod-a", "quantity": 275 }
  ]
}
```

`vehicleOverrides` only changes predefined fleet entries. `customVehicles`
creates run-scoped vehicles that are validated, included in the simulation
fingerprint, and appended to the effective fleet consumed by recovery
optimization. IDs must be unique across predefined and custom vehicles;
capacity must be a positive integer no greater than 1,000,000. Warehouse
creation remains outside the MVP contract; only inventory at predefined
facilities can be overridden. Workbook business imports do not create vehicles.

Response `201` (an implementation may initially return `queued` and later advance through `processing`):

```json
{
  "id": "sim-jakarta-20250304",
  "scenarioId": "scenario-jakarta-20250304",
  "status": "completed",
  "createdAt": "2026-08-09T10:15:00.000Z",
  "completedAt": "2026-08-09T10:15:04.000Z",
  "modelVersion": "indonesia-road-corridor-flood-exposure-v1",
  "optimizerVersion": "recovery-planner-1.0.0",
  "dataMode": "historical_snapshot",
  "historicalDataStatus": "available"
}
```

`completedAt`, `modelVersion`, and `optimizerVersion` may be absent while queued/processing. A failed resource includes the standard error object in `error`. Relevant statuses: `201`, `400`, `404`, `409`, `422`, `500`.

### GET /api/simulations/{simulationId}

Purpose: retrieve/poll simulation metadata without exposing ML internals. Consumers: Scenario flow and Simulation Details. Path param: `simulationId` string. Query params/body: none. Schema: `simulationSchema`.

Response `200` is the complete simulation JSON shown above. Pending example:

```json
{
  "id": "sim-jakarta-20250304",
  "scenarioId": "scenario-jakarta-20250304",
  "status": "processing",
  "createdAt": "2026-08-09T10:15:00.000Z",
  "dataMode": "historical_snapshot",
  "historicalDataStatus": "offline_snapshot"
}
```

Relevant statuses: `200`, `404`, `500`.

### GET /api/simulations/{simulationId}/disruption

Purpose: return backend/AI-owned road risk, route geometry, entity impact, and operational exposure. Consumer: Disruption Map. Path param: `simulationId`. Query params/body: none. Schema: `disruptionAnalysisSchema` in `fe/src/domain/disruption.ts`.

Route semantics are stage-specific. A disruption route with `type: "baseline"` is the normal NetworkX shortest path. The legacy `type: "recovery"` value means a risk-aware, pre-optimization NetworkX candidate; it is not proof of optimizer selection. A final selected recovery route exists only when its route ID is referenced by a successful (`ready` or `partial`) recovery outcome or logistics action. A `no-feasible-plan` result has no selected recovery route even when disruption candidates remain available for analysis.

Disruption business-impact semantics:

- `roadSegmentsAtRisk` counts only analyzed road segments in the `high` or `critical` routing bands.
- An order is at risk when its requested product depends on a supplier whose supplier-to-factory baseline route is High/Critical, or when that order's own preferred-warehouse-to-store baseline route is High/Critical. Unrelated routes sharing a warehouse or store do not propagate risk to the order.
- `salesExposure` is the gross requested value of those directly exposed orders (`quantity * unitPrice`). It is presented as **Nilai Pesanan Berisiko**, not actual lost sales, and is distinct from the residual unfulfilled sales-exposure KPI on the Impact page.
- Priority issues are route-derived and sorted stably from Critical to High to Medium to Low.

Response `200`:

```json
{
  "simulationId": "sim-jakarta-20250304",
  "facilities": [{ "id": "wh-east", "name": "Warehouse East", "kind": "warehouse", "location": { "type": "Point", "coordinates": [106.913, -6.229] } }],
  "historicalFloodGeometry": { "type": "MultiPolygon", "coordinates": [[[[106.815, -6.12], [106.9, -6.12], [106.91, -6.19], [106.815, -6.12]]]] },
  "roads": [{
    "segmentId": "road-gunung-sahari",
    "roadName": "Jl. Gunung Sahari",
    "geometry": { "type": "LineString", "coordinates": [[106.832, -6.145], [106.846, -6.177]] },
    "riskProbability": 0.82,
    "riskLevel": "high",
    "estimatedDelayMinutes": 48,
    "riskFactors": [{ "id": "historical", "label": "Historical exposure" }],
    "affectedSupplierIds": ["sup-a"],
    "affectedWarehouseIds": ["wh-east"],
    "affectedOrderIds": ["ORD-008"]
  }],
  "routes": [{
    "id": "route-baseline",
    "type": "baseline",
    "originFacilityId": "sup-a",
    "destinationFacilityId": "wh-east",
    "geometry": { "type": "MultiLineString", "coordinates": [[[106.826, -6.139], [106.913, -6.229]]] },
    "distanceKm": 18.4,
    "etaMinutes": 27,
    "floodExposure": "high",
    "floodExposureProbability": 0.82,
    "affectedRoadSegmentIds": ["road-gunung-sahari"]
  }],
  "impact": {
    "impactedSupplierIds": ["sup-a"],
    "impactedWarehouseIds": ["wh-east"],
    "impactedOrderIds": ["ORD-008"],
    "roadSegmentsAtRisk": 17,
    "salesExposure": { "amount": 8200000, "currency": "IDR" },
    "issues": [{ "id": "issue-1", "severity": "critical", "subject": "Supplier A inbound route", "description": "High estimated disruption risk requires route review." }]
  }
}
```

Relevant statuses: `200`, `404`, `409` (simulation not completed), `500`.

### POST /api/simulations/{simulationId}/recovery

Purpose: request optimizer-generated coordinated manufacturing, logistics, and commerce recovery. Consumer: Generate Recovery Plan action. Path param: `simulationId`. Query params: none. Schemas: request `recoveryGenerationRequestSchema`; response `recoveryPlanSchema`.

Request JSON (empty constraints are valid):

```json
{
  "constraints": {
    "allowSubstitution": true,
    "maxAdditionalDelayMinutes": 60
  }
}
```

Response `201` may be a complete plan (same shape as the GET response below) or pending:

```json
{
  "id": "plan-jakarta-001",
  "simulationId": "sim-jakarta-20250304",
  "createdAt": "2026-08-09T10:16:00.000Z",
  "status": "queued"
}
```

Relevant statuses: `201`, `400`, `404`, `409` (simulation not ready or generation already active), `422`, `500`.

### GET /api/simulations/{simulationId}/recovery

Purpose: retrieve/poll the optimizer result. Consumer: Recovery Plan. Path param: `simulationId`. Query params/body: none. Schema: `recoveryPlanSchema` discriminated by `status`.

Response `200` (complete example):

```json
{
  "id": "plan-jakarta-001",
  "simulationId": "sim-jakarta-20250304",
  "status": "partial",
  "createdAt": "2026-08-09T10:16:00.000Z",
  "completedAt": "2026-08-09T10:16:03.000Z",
  "summary": { "risksMitigated": 6, "operationalChanges": 9, "recoverableOrders": 18, "totalOrders": 20 },
  "manufacturingActions": [{
    "id": "mfg-a", "productId": "prod-a", "productName": "Product A", "baselineQuantity": 1000, "recoveryQuantity": 650, "changeQuantity": -350,
    "what": "Reduce Product A output and reserve constrained material.",
    "why": "Supplier A availability is projected to be delayed.",
    "expectedImpact": "Preserves shared capacity for priority orders."
  }],
  "manufacturingExplanation": {
    "reason": "Plan-level explanation grounded in active capacity/material evidence and all manufacturing actions.",
    "expectedImpact": "Plan-level fulfillment impact computed from baseline and recovery order outcomes."
  },
  "logisticsActions": [{
    "id": "log-1", "orderId": "ORD-008", "originalWarehouseId": "wh-east", "originalWarehouseName": "Warehouse East", "recoveryWarehouseId": "wh-west", "recoveryWarehouseName": "Warehouse West", "vehicleId": "V-02",
    "baselineRouteId": "route-baseline", "recoveryRouteId": "route-recovery", "baselineEtaMinutes": 27, "recoveryEtaMinutes": 35, "baselineFloodExposure": "high", "recoveryFloodExposure": "low", "action": "reallocate-reroute",
    "what": "Reallocate and reroute ORD-008.", "why": "The baseline corridor has high disruption risk.", "expectedImpact": "Reduces exposure with an eight-minute ETA increase."
  }],
  "commerceActions": [{
    "id": "com-1", "orderId": "ORD-014", "storeId": "store-c", "storeName": "Store C", "requestedProductId": "prod-a", "requestedProductName": "Product A", "requestedQuantity": 100, "priority": "critical", "action": "split-substitute",
    "allocations": [{ "productId": "prod-a", "productName": "Product A", "quantity": 65 }, { "productId": "prod-b", "productName": "Product B", "quantity": 35 }],
    "what": "Split the order and substitute 35 units.", "why": "Product A is constrained.", "expectedImpact": "Maximizes fulfillment."
  }],
  "possibleNextActions": ["Delay selected non-critical orders"]
}
```

`priority` is the order's input priority (`normal`, `high`, or `critical`), not a separate optimizer action. Consumers
must determine full, partial, or zero fulfillment from the sum of `allocations[].quantity` compared with
`requestedQuantity`. The legacy `prioritize` action is emitted for a fully fulfilled critical-priority order; it must
not be presented as evidence that the optimizer created an additional prioritization step.

Logistics action semantics are based on actual allocation outcomes. `reroute` means an allocated order kept its
warehouse but changed route, `reallocate` means its warehouse changed, and `reallocate-reroute` means both changed.
`allocate` means an order with no baseline allocation received a recovery warehouse, route, and vehicle. For
`allocate`, `originalWarehouseId`, `originalWarehouseName`, `baselineRouteId`, `baselineEtaMinutes`, and
`baselineFloodExposure` are omitted (or `null` for consumers that preserve nullable fields); preferred warehouses
and nominal routes must not be presented as actual baseline assignments.

For `queued`/`processing`, only `id`, `simulationId`, `createdAt`, and `status` are required. For `failed`, include `error`. Relevant statuses: `200`, `404`, `500`.

### GET /api/simulations/{simulationId}/impact

Purpose: return backend-owned baseline and recovery KPI values. Consumer: Impact Analysis. Path param: `simulationId`. Query params/body: none. Schema: `impactComparisonSchema` in `fe/src/domain/impact.ts`.

Response `200`:

```json
{
  "simulationId": "sim-jakarta-20250304",
  "recoveryStatus": "partial",
  "businessDataSource": "demo",
  "metrics": [
    { "key": "orders-fulfilled", "baseline": 13, "recovery": 18, "total": 20 },
    { "key": "on-time-delivery", "baseline": 0.55, "recovery": 0.85 },
    { "key": "failed-orders", "baseline": 5, "recovery": 1 },
    { "key": "average-delay", "baseline": 128, "recovery": 42, "baselineObservationCount": 15, "recoveryObservationCount": 19 },
    { "key": "sales-exposure-risk", "baseline": 8200000, "recovery": 2100000, "currency": "IDR" }
  ],
  "actionCounts": { "manufacturing": 2, "logistics": 4, "commerce": 3 }
}
```

All five metric keys are required once and are semantic identifiers, not UI labels. `recoveryStatus` is the actual optimizer result and must drive feasible/partial/no-feasible presentation; clients must not infer it from KPI values. Average-delay observation counts let clients render `N/A` when no orders were delivered. Relevant statuses: `200`, `404`, `409` (recovery not complete), `500`.

## Domain Structure and Referential Rules

- Scenario owns facilities, vehicles, products, materials, inventory, and orders. Referenced IDs must resolve within the scenario snapshot.
- Road risk references supplier, warehouse, and order IDs. Route endpoints reference facility IDs; risky segments reference road `segmentId` values.
- Recovery actions include both stable IDs and snapshot display names. IDs drive joins; names preserve the optimizer result as an auditable snapshot.
- Every recommendation includes raw decision fields plus `what`, `why`, and `expectedImpact`. Those explanation strings are backend/optimizer output, not generated by React.
- Impact metric keys are fixed contract vocabulary. Labels and formatting are frontend-owned.
- A complete response must be internally coherent. Counts such as `recoverableOrders` and `actionCounts` must match backend results; the frontend does not recompute optimization outcomes.

## Data Ownership

### Frontend-Owned Responsibilities

Rendering, interaction, loading/error/empty states, selected map segment/tabs/modals, sorting/filtering, locale date display, IDR formatting, percentage display, visual comparisons, safe arithmetic presentation deltas, and metric labels.

### Backend-Owned Responsibilities

Orchestration, process-local state, entity normalization, endpoint semantics, simulation lifecycle, affected entities, supply-chain impact, sales exposure, KPI values, version metadata, and consistent failure envelopes. The current MVP has no API authentication or tenancy.

### AI-Owned Responsibilities

Flood disruption probability, risk model output, contributing risk factors, and model version. The API normalizes AI output to the documented probability/risk schemas.

### Optimizer-Owned Responsibilities

Recoverability and coordinated manufacturing, logistics, and commerce decisions, including all what/why/expected-impact explanations and optimizer version. The frontend never reconstructs OR-Tools decisions. Supplier-to-factory and warehouse-to-store road legs are explicit; factory-to-warehouse transfer is an aggregate MVP abstraction rather than a separately routed vehicle leg.

### Routing-Owned Responsibilities

Baseline/recovery route geometry, distance, ETA, flood exposure probability/category, and affected road-segment IDs. OSMnx/NetworkX output must be normalized to GeoJSON before it reaches the frontend.

## Switching from Mock to Real Backend

1. Use the implemented FastAPI endpoints summarized above, preserving paths, camelCase JSON, states, status codes, and error envelopes.
2. Validate response examples against the Zod schemas or generate equivalent Pydantic models.
3. Configure FastAPI CORS for `http://localhost:3000` in development and the exact deployed frontend origin in production.
4. Run FastAPI on `http://localhost:8000`.
5. Set `NEXT_PUBLIC_DATA_SOURCE=api` and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local`.
6. Restart the Next.js process. Verify Scenario -> Simulation -> Disruption -> Recovery -> Impact.
7. Do not import or run MSW on the backend. The frontend provider automatically skips MSW in API mode.

No page or visual component modification is required if FastAPI satisfies this contract.

## Compatibility and Versioning

This is v1.0. Additive optional fields are compatible. Removing/renaming fields, changing enum values/units, changing probability scale, or changing endpoint paths is breaking and requires a versioned contract plus coordinated frontend release. Do not return formatted currency, percentages, or duration strings. Keep internal ML, routing, and optimizer implementation details behind the API boundary.

## Known Integration Risks

- There is no authentication or tenancy contract. Process-local snapshot IDs are identifiers, not authorization; introduce security as a separate cross-cutting contract before production.
- v1 uses polling with a fixed one-second interval and has no cancellation endpoint, progress percentage, pagination, or WebSocket events.
- The scenario selector currently targets one historical Jakarta resource; future scenario discovery should be an additive endpoint, not a breaking replacement.
- Simulation, recovery, custom snapshot, and idempotency state is process-local and resets on backend restart. This is an explicit controlled-MVP limitation.
