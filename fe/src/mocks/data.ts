import type { DisruptionAnalysis } from "@/domain/disruption";
import type { ImpactComparison } from "@/domain/impact";
import type { RecoveryPlan } from "@/domain/recovery";
import type { Scenario, Simulation } from "@/domain/scenario";

const facilities: Scenario["facilities"] = [
  { id: "sup-a", name: "Supplier A", kind: "supplier", location: { type: "Point", coordinates: [106.826, -6.139] } },
  { id: "sup-b", name: "Supplier B", kind: "supplier", location: { type: "Point", coordinates: [106.91, -6.195] } },
  { id: "fac-1", name: "Nusantara Foods Factory", kind: "factory", location: { type: "Point", coordinates: [106.875, -6.236] } },
  { id: "wh-east", name: "Warehouse East", kind: "warehouse", location: { type: "Point", coordinates: [106.913, -6.229] } },
  { id: "wh-west", name: "Warehouse West", kind: "warehouse", location: { type: "Point", coordinates: [106.77, -6.188] } },
  { id: "store-a", name: "Store A", kind: "store", location: { type: "Point", coordinates: [106.808, -6.171] } },
  { id: "store-b", name: "Store B", kind: "store", location: { type: "Point", coordinates: [106.852, -6.161] } },
  { id: "store-c", name: "Store C", kind: "store", location: { type: "Point", coordinates: [106.893, -6.155] } },
  { id: "store-d", name: "Store D", kind: "store", location: { type: "Point", coordinates: [106.927, -6.176] } },
  { id: "store-e", name: "Store E", kind: "store", location: { type: "Point", coordinates: [106.827, -6.22] } },
];

export const scenarioFixture: Scenario = {
  id: "scenario-jakarta-20250304", name: "Jakarta Flood — 04 March 2025", mode: "historical-replay",
  location: "Jakarta", eventDate: "2025-03-04", eventType: "Urban Flood",
  dataSources: { mode: "historical_snapshot", historicalStatus: "available", operationalStatus: "simulated", historicalProvider: "local historical archive", snapshotId: "jakarta-2025-03-04-v1" },
  companyName: "Nusantara Foods", facilities,
  vehicles: [
    { id: "V-01", label: "Box Truck 01", capacityUnits: 800 },
    { id: "V-02", label: "Box Truck 02", capacityUnits: 800 },
    { id: "V-03", label: "Van 03", capacityUnits: 450 },
  ],
  products: [{ id: "prod-a", name: "Product A", unit: "units" }, { id: "prod-b", name: "Product B", unit: "units" }],
  materials: [
    { id: "mat-a", name: "Primary Ingredient", supplierId: "sup-a", productIds: ["prod-a"] },
    { id: "mat-b", name: "Shared Packaging", supplierId: "sup-b", productIds: ["prod-a", "prod-b"] },
  ],
  inventory: [
    { facilityId: "wh-east", productId: "prod-a", quantity: 420, unit: "units" },
    { facilityId: "wh-west", productId: "prod-a", quantity: 310, unit: "units" },
    { facilityId: "wh-west", productId: "prod-b", quantity: 500, unit: "units" },
  ],
  orders: Array.from({ length: 20 }, (_, index) => ({
    id: `ORD-${String(index + 1).padStart(3, "0")}`, storeId: `store-${["a", "b", "c", "d", "e"][index % 5]}`,
    productId: index % 3 === 0 ? "prod-b" : "prod-a", quantity: 60 + (index % 5) * 10,
    priority: index === 7 || index === 13 ? "critical" : index % 4 === 0 ? "high" : "normal",
  })),
};

export const simulationFixture: Simulation = {
  id: "sim-jakarta-20250304", scenarioId: scenarioFixture.id, status: "completed", createdAt: "2026-08-09T10:15:00.000Z", completedAt: "2026-08-09T10:15:04.000Z",
  modelVersion: "flood-risk-0.3.0-demo", optimizerVersion: "recovery-planner-0.2.0-demo", dataMode: "historical_snapshot", historicalDataStatus: "available",
};

export const disruptionFixture: DisruptionAnalysis = {
  simulationId: simulationFixture.id, facilities,
  historicalFloodGeometry: { type: "Polygon", coordinates: [[[106.815, -6.12], [106.9, -6.12], [106.91, -6.19], [106.84, -6.205], [106.815, -6.12]]] },
  roads: [
    { segmentId: "road-gunung-sahari", roadName: "Jl. Gunung Sahari", geometry: { type: "LineString", coordinates: [[106.832, -6.145], [106.838, -6.153], [106.842, -6.164], [106.846, -6.177]] }, riskProbability: 0.82, riskLevel: "high", estimatedDelayMinutes: 48, riskFactors: [{ id: "historical", label: "Historical exposure" }, { id: "elevation", label: "Low elevation" }], affectedSupplierIds: ["sup-a"], affectedWarehouseIds: ["wh-east"], affectedOrderIds: ["ORD-008", "ORD-014"] },
    { segmentId: "road-kemayoran", roadName: "Jl. Benyamin Sueb", geometry: { type: "LineString", coordinates: [[106.86, -6.16], [106.875, -6.17], [106.89, -6.185]] }, riskProbability: 0.68, riskLevel: "medium", estimatedDelayMinutes: 31, riskFactors: [{ id: "drainage", label: "Drainage pressure" }], affectedSupplierIds: [], affectedWarehouseIds: ["wh-east"], affectedOrderIds: ["ORD-005", "ORD-009"] },
  ],
  routes: [
    { id: "route-baseline", type: "baseline", originFacilityId: "sup-a", destinationFacilityId: "wh-east", geometry: { type: "LineString", coordinates: [[106.826, -6.139], [106.842, -6.164], [106.875, -6.19], [106.913, -6.229]] }, distanceKm: 18.4, etaMinutes: 27, floodExposure: "high", floodExposureProbability: 0.82, affectedRoadSegmentIds: ["road-gunung-sahari", "road-kemayoran"] },
    { id: "route-recovery", type: "recovery", originFacilityId: "sup-a", destinationFacilityId: "fac-1", geometry: { type: "LineString", coordinates: [[106.826, -6.139], [106.8, -6.17], [106.79, -6.205], [106.83, -6.238], [106.875, -6.236]] }, distanceKm: 24.8, etaMinutes: 35, floodExposure: "low", floodExposureProbability: 0.2, affectedRoadSegmentIds: [] },
  ],
  impact: {
    impactedSupplierIds: ["sup-a"], impactedWarehouseIds: ["wh-east"], impactedOrderIds: ["ORD-005", "ORD-008", "ORD-009", "ORD-014", "ORD-017", "ORD-020"],
    roadSegmentsAtRisk: 17, salesExposure: { amount: 8_200_000, currency: "IDR" },
    issues: [
      { id: "issue-1", severity: "critical", subject: "Supplier A inbound route", description: "High estimated disruption risk requires immediate route review to maintain material availability." },
      { id: "issue-2", severity: "high", subject: "Warehouse East ? Store C", description: "Elevated disruption probability may add more than 45 minutes to delivery." },
      { id: "issue-3", severity: "high", subject: "ORD-014", description: "Outbound delivery is at risk of missing its dispatch window." },
    ],
  },
};

export const recoveryFixture: RecoveryPlan = {
  id: "plan-jakarta-001", simulationId: simulationFixture.id, status: "partial", createdAt: "2026-08-09T10:16:00.000Z", completedAt: "2026-08-09T10:16:03.000Z",
  summary: { risksMitigated: 6, operationalChanges: 9, recoverableOrders: 18, totalOrders: 20 },
  manufacturingActions: [
    { id: "mfg-a", productId: "prod-a", productName: "Product A", baselineQuantity: 1000, recoveryQuantity: 650, changeQuantity: -350, what: "Reduce Product A output and reserve constrained material.", why: "Supplier A availability is projected to be delayed by high-risk inbound road segments.", expectedImpact: "Preserves shared capacity while protecting priority Product A orders." },
    { id: "mfg-b", productId: "prod-b", productName: "Product B", baselineQuantity: 500, recoveryQuantity: 750, changeQuantity: 250, what: "Reallocate available capacity to Product B.", why: "Product B relies on unaffected Supplier B material and available packaging.", expectedImpact: "Projects Rp 1.2 juta less sales exposure through authorized substitution." },
  ],
  logisticsActions: [
    { id: "log-1", orderId: "ORD-008", originalWarehouseId: "wh-east", originalWarehouseName: "Warehouse East", recoveryWarehouseId: "wh-west", recoveryWarehouseName: "Warehouse West", vehicleId: "V-02", baselineRouteId: "route-baseline", recoveryRouteId: "route-recovery", baselineEtaMinutes: 27, recoveryEtaMinutes: 35, baselineFloodExposure: "high", recoveryFloodExposure: "low", action: "reallocate-reroute", what: "Reallocate ORD-008 to Warehouse West and Vehicle V-02, then use the recovery route.", why: "The normal Warehouse East corridor has 82% estimated disruption risk.", expectedImpact: "Reduces flood exposure while maintaining delivery continuity with an estimated 8-minute ETA increase." },
  ],
  commerceActions: [
    { id: "com-1", orderId: "ORD-014", storeId: "store-c", storeName: "Store C", requestedProductId: "prod-a", requestedProductName: "Product A", requestedQuantity: 100, action: "split-substitute", allocations: [{ productId: "prod-a", productName: "Product A", quantity: 65 }, { productId: "prod-b", productName: "Product B", quantity: 35 }], what: "Split ORD-014 and substitute 35 units with Product B.", why: "Product A is constrained by the projected Supplier A delay.", expectedImpact: "Projects preservation of Rp 1.4 juta in order value while maximizing fulfillment." },
  ],
  possibleNextActions: ["Delay selected non-critical orders", "Increase substitution allowance", "Allow additional warehouse capacity"],
};

export const impactFixture: ImpactComparison = {
  simulationId: simulationFixture.id,
  metrics: [
    { key: "orders-fulfilled", baseline: 13, recovery: 18, total: 20 },
    { key: "on-time-delivery", baseline: 0.55, recovery: 0.85 },
    { key: "failed-orders", baseline: 5, recovery: 1 },
    { key: "average-delay", baseline: 128, recovery: 42 },
    { key: "sales-exposure-risk", baseline: 8_200_000, recovery: 2_100_000, currency: "IDR" },
  ],
  actionCounts: { manufacturing: 2, logistics: 4, commerce: 3 },
};
