import type { DisruptionAnalysis } from "@/domain/disruption";
import type { ImpactComparison } from "@/domain/impact";
import type { RecoveryPlan } from "@/domain/recovery";
import type { Scenario, Simulation } from "@/domain/scenario";

const facilities: Scenario["facilities"] = [
  { id: "sup-a", name: "Pemasok A", kind: "supplier", location: { type: "Point", coordinates: [106.826, -6.139] } },
  { id: "sup-b", name: "Pemasok B", kind: "supplier", location: { type: "Point", coordinates: [106.91, -6.195] } },
  { id: "fac-1", name: "Pabrik Nusantara Foods", kind: "factory", location: { type: "Point", coordinates: [106.875, -6.236] } },
  { id: "wh-east", name: "Gudang Timur", kind: "warehouse", location: { type: "Point", coordinates: [106.913, -6.229] } },
  { id: "wh-west", name: "Gudang Barat", kind: "warehouse", location: { type: "Point", coordinates: [106.77, -6.188] } },
  { id: "store-a", name: "Toko A", kind: "store", location: { type: "Point", coordinates: [106.808, -6.171] } },
  { id: "store-b", name: "Toko B", kind: "store", location: { type: "Point", coordinates: [106.852, -6.161] } },
  { id: "store-c", name: "Toko C", kind: "store", location: { type: "Point", coordinates: [106.893, -6.155] } },
  { id: "store-d", name: "Toko D", kind: "store", location: { type: "Point", coordinates: [106.927, -6.176] } },
  { id: "store-e", name: "Toko E", kind: "store", location: { type: "Point", coordinates: [106.827, -6.22] } },
];

export const scenarioFixture: Scenario = {
  id: "scenario-jakarta-20250304", name: "Banjir Jakarta — 04 Maret 2025", mode: "historical-replay",
  location: "Jakarta", eventDate: "2025-03-04", eventType: "Banjir Perkotaan",
  dataSources: { mode: "historical_snapshot", historicalStatus: "available", operationalStatus: "simulated", historicalProvider: "arsip historis lokal", snapshotId: "jakarta-2025-03-04-v1" },
  companyName: "Nusantara Foods", facilities,
  vehicles: [
    { id: "V-01", label: "Truk Boks 01", capacityUnits: 800, available: true },
    { id: "V-02", label: "Truk Boks 02", capacityUnits: 800, available: true },
    { id: "V-03", label: "Mobil Van 03", capacityUnits: 450, available: true },
  ],
  products: [{ id: "prod-a", name: "Produk A", unit: "unit" }, { id: "prod-b", name: "Produk B", unit: "unit" }],
  materials: [
    { id: "mat-a", name: "Bahan Utama", supplierId: "sup-a", productIds: ["prod-a"] },
    { id: "mat-b", name: "Kemasan Bersama", supplierId: "sup-b", productIds: ["prod-a", "prod-b"] },
  ],
  inventory: [
    { facilityId: "wh-east", productId: "prod-a", quantity: 420, unit: "unit" },
    { facilityId: "wh-west", productId: "prod-a", quantity: 310, unit: "unit" },
    { facilityId: "wh-west", productId: "prod-b", quantity: 500, unit: "unit" },
  ],
  orders: Array.from({ length: 20 }, (_, index) => ({
    id: `ORD-${String(index + 1).padStart(3, "0")}`, storeId: `store-${["a", "b", "c", "d", "e"][index % 5]}`,
    productId: index % 3 === 0 ? "prod-b" : "prod-a", quantity: 60 + (index % 5) * 10,
    priority: index === 7 || index === 13 ? "critical" : index % 4 === 0 ? "high" : "normal",
  })),
};

export const simulationFixture: Simulation = {
  id: "sim-jakarta-20250304", scenarioId: scenarioFixture.id, status: "completed", createdAt: "2026-08-09T10:15:00.000Z", completedAt: "2026-08-09T10:15:04.000Z",
  analysisMode: "historical-replay", region: "jakarta",
  modelVersion: "indonesia-road-corridor-flood-exposure-v1",
  modelProvenance: {
    trainingData: "real-historical-global-flood-database-indonesia",
    source: "Global Flood Database / MODIS_EVENTS/V1",
    target: "roadCorridorFloodExposure",
    algorithm: "RandomForestClassifier",
    trainingScope: "32 kejadian banjir historis di 13 region Indonesia",
    deploymentScope: "Jakarta sebagai pilot inferensi/demo",
    trainingEvents: 32,
    trainingRegions: 13,
    jakartaValidationStatus: "not_validated",
    probabilitySemantics: "Probabilitas paparan banjir koridor jalan, bukan kepastian jalan ditutup",
  },
  optimizerVersion: "cp-sat-connected-v2", dataMode: "historical_snapshot", historicalDataStatus: "available",
  businessDataSource: "demo",
};

export const disruptionFixture: DisruptionAnalysis = {
  simulationId: simulationFixture.id, facilities,
  historicalFloodGeometry: { type: "Polygon", coordinates: [[[106.815, -6.12], [106.9, -6.12], [106.91, -6.19], [106.84, -6.205], [106.815, -6.12]]] },
  roads: [
    { segmentId: "road-gunung-sahari", roadName: "Jl. Gunung Sahari", highwayClass: "primary", osmWayIds: ["749966273"], geometry: { type: "LineString", coordinates: [[106.832, -6.145], [106.838, -6.153], [106.842, -6.164], [106.846, -6.177]] }, riskProbability: 0.82, riskLevel: "high", estimatedDelayMinutes: 48, riskFactors: [{ id: "historical", label: "Paparan historis" }, { id: "elevation", label: "Elevasi rendah" }], affectedSupplierIds: ["sup-a"], affectedWarehouseIds: ["wh-east"], affectedOrderIds: ["ORD-008", "ORD-014"] },
    { segmentId: "road-kemayoran", roadName: "Jl. Benyamin Sueb", highwayClass: "trunk", osmWayIds: ["839201948"], geometry: { type: "LineString", coordinates: [[106.86, -6.16], [106.875, -6.17], [106.89, -6.185]] }, riskProbability: 0.68, riskLevel: "medium", estimatedDelayMinutes: 31, riskFactors: [{ id: "drainage", label: "Tekanan drainase" }], affectedSupplierIds: [], affectedWarehouseIds: ["wh-east"], affectedOrderIds: ["ORD-005", "ORD-009"] },
  ],
  routes: [
    { id: "route-baseline", type: "baseline", originFacilityId: "sup-a", destinationFacilityId: "wh-east", geometry: { type: "LineString", coordinates: [[106.826, -6.139], [106.842, -6.164], [106.875, -6.19], [106.913, -6.229]] }, distanceKm: 18.4, etaMinutes: 27, floodExposure: "high", floodExposureProbability: 0.82, affectedRoadSegmentIds: ["road-gunung-sahari", "road-kemayoran"] },
    { id: "route-recovery", type: "recovery", originFacilityId: "sup-a", destinationFacilityId: "fac-1", geometry: { type: "LineString", coordinates: [[106.826, -6.139], [106.8, -6.17], [106.79, -6.205], [106.83, -6.238], [106.875, -6.236]] }, distanceKm: 24.8, etaMinutes: 35, floodExposure: "low", floodExposureProbability: 0.2, affectedRoadSegmentIds: [] },
  ],
  impact: {
    impactedSupplierIds: ["sup-a"], impactedWarehouseIds: ["wh-east"], impactedOrderIds: ["ORD-005", "ORD-008", "ORD-009", "ORD-014", "ORD-017", "ORD-020"],
    roadSegmentsAtRisk: 17, salesExposure: { amount: 8_200_000, currency: "IDR" },
    issues: [
      { id: "issue-1", severity: "critical", subject: "Pemasok A rute masuk", description: "Perkiraan risiko gangguan yang tinggi memerlukan peninjauan rute segera untuk menjaga ketersediaan material." },
      { id: "issue-2", severity: "high", subject: "Gudang Timur → Toko C", description: "Peningkatan kemungkinan gangguan dapat menambah waktu pengiriman lebih dari 45 menit." },
      { id: "issue-3", severity: "high", subject: "ORD-014", description: "Pengiriman keluar berisiko melewati jadwal keberangkatan." },
    ],
  },
};

export const recoveryFixture: RecoveryPlan = {
  id: "plan-jakarta-001", simulationId: simulationFixture.id, status: "partial", createdAt: "2026-08-09T10:16:00.000Z", completedAt: "2026-08-09T10:16:03.000Z",
  summary: { risksMitigated: 6, operationalChanges: 9, recoverableOrders: 18, totalOrders: 20 },
  manufacturingActions: [
    { id: "mfg-a", productId: "prod-a", productName: "Produk A", baselineQuantity: 1000, recoveryQuantity: 650, changeQuantity: -350, what: "Kurangi produksi Produk A dari 1000 menjadi 650 unit.", why: "Perubahan ini merupakan bagian dari penyeimbangan mix produksi.", expectedImpact: "Produksi Produk A berkurang 350 unit." },
    { id: "mfg-b", productId: "prod-b", productName: "Produk B", baselineQuantity: 500, recoveryQuantity: 750, changeQuantity: 250, what: "Naikkan produksi Produk B dari 500 menjadi 750 unit.", why: "Perubahan ini merupakan bagian dari penyeimbangan mix produksi.", expectedImpact: "Produksi Produk B bertambah 250 unit." },
  ],
  manufacturingExplanation: {
    reason: "ARUNA mengalihkan kapasitas produksi dari Produk A ke Produk B berdasarkan kebutuhan pesanan dan kondisi operasional.",
    expectedImpact: "Rencana pemulihan meningkatkan pemenuhan pesanan dari 13/20 menjadi 18/20.",
  },
  logisticsActions: [
    { id: "log-1", orderId: "ORD-008", originalWarehouseId: "wh-east", originalWarehouseName: "Gudang Timur", recoveryWarehouseId: "wh-west", recoveryWarehouseName: "Gudang Barat", vehicleId: "V-02", baselineRouteId: "route-baseline", recoveryRouteId: "route-recovery", baselineEtaMinutes: 27, recoveryEtaMinutes: 35, baselineFloodExposure: "high", recoveryFloodExposure: "low", action: "reallocate-reroute", what: "Alihkan ORD-008 ke Gudang Barat dan Kendaraan V-02, lalu gunakan rute pemulihan.", why: "Koridor normal Gudang Timur memiliki perkiraan risiko gangguan sebesar 82%.", expectedImpact: "Mengurangi paparan banjir sambil menjaga kelangsungan pengiriman dengan perkiraan tambahan waktu tempuh 8 menit." },
  ],
  commerceActions: [
    { id: "com-1", orderId: "ORD-014", storeId: "store-c", storeName: "Toko C", requestedProductId: "prod-a", requestedProductName: "Produk A", requestedQuantity: 100, action: "split-substitute", allocations: [{ productId: "prod-a", productName: "Produk A", quantity: 65 }, { productId: "prod-b", productName: "Produk B", quantity: 35 }], what: "Bagi ORD-014 dan substitusikan 35 unit dengan Produk B.", why: "Produk A terkendala oleh proyeksi keterlambatan Pemasok A.", expectedImpact: "Memproyeksikan terjaganya nilai pesanan sebesar Rp 1,4 juta sekaligus memaksimalkan pemenuhan." },
  ],
  possibleNextActions: ["Tunda pesanan nonkritis yang dipilih", "Tingkatkan batas substitusi", "Izinkan kapasitas gudang tambahan"],
};

export const impactFixture: ImpactComparison = {
  simulationId: simulationFixture.id,
  recoveryStatus: "partial",
  businessDataSource: "demo",
  metrics: [
    { key: "orders-fulfilled", baseline: 13, recovery: 18, total: 20 },
    { key: "on-time-delivery", baseline: 0.55, recovery: 0.85 },
    { key: "failed-orders", baseline: 5, recovery: 1 },
    { key: "average-delay", baseline: 128, recovery: 42, baselineObservationCount: 15, recoveryObservationCount: 19 },
    { key: "sales-exposure-risk", baseline: 8_200_000, recovery: 2_100_000, currency: "IDR" },
  ],
  actionCounts: { manufacturing: 2, logistics: 4, commerce: 3 },
};
