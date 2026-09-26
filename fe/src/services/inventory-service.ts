import { inventoryOverviewSchema } from "@/domain/inventory";
import { adjustmentRequestSchema, adjustmentResponseSchema, inventoryResponseSchema, movementsResponseSchema, procurementResponseSchema, receivingRequestSchema, receivingResponseSchema } from "@/domain/inventory-api";
import { inventoryOverviewMock } from "@/mocks/inventory-data";
import { inventoryRequest, mutationHeaders, usesInventoryApi, wibDate } from "@/lib/inventory-api";
import { riskStatus } from "@/lib/inventory-risk";
import { allPages, getRisks } from "./inventory-api-data";

export const inventoryService = {
  getSuppliers: async () => {
    if (!usesInventoryApi()) return [];
    const plan = await inventoryRequest("/procurement/recommendations", procurementResponseSchema);
    return [...new Map([...plan.recommendations, ...plan.outstandingRecommendations].map((item) => [item.supplier.id, item.supplier])).values()];
  },
  getOverview: async () => {
    if (!usesInventoryApi()) return inventoryOverviewSchema.parse(inventoryOverviewMock);
    const [inventory, movements, risks] = await Promise.all([
      inventoryRequest("/inventory", inventoryResponseSchema),
      allPages((page) => inventoryRequest(`/inventory/movements?pageSize=100&page=${page}`, movementsResponseSchema)),
      getRisks(),
    ]);
    const categories = { SALE: "Kebutuhan Penjualan", STOCK_IN: "Stok Masuk", DAMAGE: "Rusak", WASTE: "Terbuang", ADJUSTMENT: "Penyesuaian" };
    return inventoryOverviewSchema.parse({
      source: "api", businessDate: wibDate(),
      materials: inventory.items.map((item) => {
        const risk = risks.items.find((candidate) => candidate.ingredientId === item.ingredientId);
        return { id: item.ingredientId, name: item.ingredientName, category: item.category ?? "—", quantity: item.currentStock, unit: item.unit, reorderLevel: risk?.reorderPoint ?? 0, predictedDemand: item.predictedRequirement, issue: riskStatus(item.riskLevel), dueLabel: risk?.projectedStockoutDate ?? "—", stockId: item.ingredientId, supplier: "—", riskReason: item.riskReason, inventoryVersion: inventory.inventoryVersion };
      }),
      movements: movements.map((item) => ({ id: item.id, materialId: item.ingredientId, materialName: item.ingredientName, category: categories[item.type], quantityChange: item.quantityChange, unit: item.unit, referenceId: item.transactionId ?? item.id, occurredAt: item.createdAt, warningLevel: null })),
    });
  },
  adjust: async (id: string, payload: unknown, key: string) => inventoryRequest(`/inventory/${encodeURIComponent(id)}/adjustments`, adjustmentResponseSchema, { method: "POST", headers: mutationHeaders(key), body: JSON.stringify(adjustmentRequestSchema.parse(payload)) }),
  receive: async (id: string, payload: unknown, key: string) => inventoryRequest(`/inventory/${encodeURIComponent(id)}/stock-in`, receivingResponseSchema, { method: "POST", headers: mutationHeaders(key), body: JSON.stringify(receivingRequestSchema.parse(payload)) }),
};
