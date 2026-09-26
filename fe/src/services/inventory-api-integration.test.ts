import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { InventoryApiError } from "@/lib/inventory-api";
import { invalidateInventoryQueries } from "@/hooks/inventory-query-invalidation";
import { posSimulatorService } from "./pos-simulator-service";
import { demandForecastService } from "./demand-forecast-service";
import { inventoryService } from "./inventory-service";
import { optimizationPlanService } from "./optimization-plan-service";
import { salesService } from "./sales-service";

vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "api", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
const instant = "2026-09-26T08:00:00Z";
const product = { id: "P011", name: "Jus Mangga", price: 20000, currency: "IDR", isActive: true };
const transaction = { id: "txn-1", createdAt: instant, totalItems: 1, totalAmount: 20000, currency: "IDR", items: [{ productId: "P011", productName: "Jus Mangga", quantity: 1, unitPrice: 20000, subtotal: 20000 }], ingredientConsumption: [{ ingredientId: "ing_mangga", ingredientName: "Mangga", quantity: .25, unit: "kg" }] };
const ingredient = { ingredientId: "ing_mangga", ingredientName: "Mangga", currentStock: 10, category: "Buah", unit: "kg", predictedRequirement: 13.5, requirementHorizonDays: 3, riskLevel: "HIGH", riskReason: "Projected shortage", updatedAt: instant };
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
afterEach(() => vi.unstubAllGlobals());

describe("inventory API integration boundary", () => {
  it("uses backend product IDs/prices without fabricating recipe data or an initial order", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ products: [product] })));
    const catalogue = await posSimulatorService.getCatalogue();
    expect(catalogue.source).toBe("api");
    expect(catalogue.initialOrder).toEqual([]);
    expect(catalogue.products[0]).toMatchObject({ id: "P011", price: 20000 });
    expect(catalogue.products[0].materialUsageGrams).toBeUndefined();
  });
  it("posts the internal checkout origin and preserves the same retry key", async () => {
    const fetch = vi.fn().mockImplementation(async () => reply({ transaction }));
    vi.stubGlobal("fetch", fetch);
    for (let i = 0; i < 2; i++) expect(await posSimulatorService.checkout({ items: [{ productId: "P011", quantity: 1 }] }, "order-key")).toEqual({ status: "success", transactionId: "txn-1" });
    for (const call of fetch.mock.calls) {
      expect(call[1].headers["Idempotency-Key"]).toBe("order-key");
      expect(JSON.parse(call[1].body)).toEqual({ source: "POS_SIMULATOR", items: [{ productId: "P011", quantity: 1 }] });
    }
  });
  it("converts backend shortage quantities into the configured ingredient unit", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(reply({ error: { code: "INSUFFICIENT_INVENTORY", message: "Shortage", details: { shortages: [{ ingredientId: "ing_mangga", requiredBase: 12500000, availableBase: 10000000, shortfallBase: 2500000 }] } } }, 409)).mockResolvedValueOnce(reply({ items: [ingredient] }));
    vi.stubGlobal("fetch", fetch);
    expect(await posSimulatorService.checkout({ items: [{ productId: "P011", quantity: 50 }] })).toEqual({ status: "insufficient-stock", shortages: [{ materialName: "Mangga", required: 12.5, available: 10, shortage: 2.5, unit: "kg" }] });
  });
  it("preserves domain conflict codes instead of treating them as success or switching to mocks", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ error: { code: "STALE_RECOMMENDATION", message: "Refresh plan", details: null } }, 409)));
    await expect(optimizationPlanService.decide("rec-1", "APPROVED")).rejects.toMatchObject({ name: "InventoryApiError", code: "STALE_RECOMMENDATION", status: 409 });
  });
  it("derives forecast totals from the same daily series and keeps BOM totals separate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(reply({ products: [product] })).mockResolvedValueOnce(reply({
      product: { id: "P011", name: "Jus Mangga" }, horizonDays: 3, generatedAt: instant, model: { name: "training-profile-mean", version: "v1" }, source: "FALLBACK", isSynthetic: true,
      history: [{ date: "2026-09-25", actualDemand: 10 }], forecast: [{ date: "2026-09-26", horizon: 1, predictedDemand: 15 }, { date: "2026-09-27", horizon: 2, predictedDemand: 18 }, { date: "2026-09-28", horizon: 3, predictedDemand: 22 }],
      ingredientRequirements: [{ ingredientId: "ing_mangga", ingredientName: "Mangga", totalRequired: 13.75, unit: "kg" }],
    })));
    const forecast = await demandForecastService.getForecast("P011");
    expect(forecast.totalPredictedSales).toBe(55);
    expect(forecast.details.reduce((sum, row) => sum + row.predictedSales, 0)).toBe(55);
    expect(forecast.requirements).toEqual([{ name: "Mangga", quantity: 13.75, unit: "kg" }]);
    expect(forecast.forecastSource).toBe("FALLBACK");
  });
  it("loads persisted transaction details and consumption without exposing source", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ transaction: { ...transaction, source: "POS_SIMULATOR" } })));
    const detail = await salesService.getTransaction("txn-1");
    expect(detail?.inventoryDeductions).toEqual([{ materialName: "Mangga", quantity: .25, unit: "kg" }]);
    expect(detail).not.toHaveProperty("source");
  });
  it("posts validated physical counts and receiving payloads with idempotency", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(reply({ inventory: ingredient, movement: null })).mockResolvedValueOnce(reply({ inventory: ingredient, movementId: "move-1" }));
    vi.stubGlobal("fetch", fetch);
    await inventoryService.adjust("ing_mangga", { countedStock: 10, unit: "kg", reason: "PHYSICAL_COUNT", note: null, expectedInventoryVersion: 7 }, "count-key");
    await inventoryService.receive("ing_mangga", { quantity: 5, unit: "kg", supplierId: "supplier-1", note: null, recommendationId: "rec-1", externalReceiptId: "receipt-1" }, "receipt-key");
    expect(fetch.mock.calls[0][1].headers["Idempotency-Key"]).toBe("count-key");
    expect(JSON.parse(fetch.mock.calls[0][1].body).expectedInventoryVersion).toBe(7);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toMatchObject({ recommendationId: "rec-1", externalReceiptId: "receipt-1" });
    await expect(inventoryService.receive("ing_mangga", { quantity: -1 }, "bad")).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("invalidates all affected inventory views while preserving legacy query state", async () => {
    const client = new QueryClient();
    const keys = [["inventory", "overview"], ["inventory-sales", "overview"], ["inventory-dashboard", "summary"], ["inventory-demand", "forecast"], ["inventory-optimization", "plan"], ["legacy", "simulation"]];
    for (const key of keys) client.setQueryData(key, {});
    await invalidateInventoryQueries(client);
    for (const key of keys.slice(0, -1)) expect(client.getQueryState(key)?.isInvalidated).toBe(true);
    expect(client.getQueryState(keys.at(-1)!)?.isInvalidated).toBe(false);
  });
  it("rejects malformed responses at the Zod boundary", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ products: [{ ...product, price: "20000" }] })));
    await expect(posSimulatorService.getCatalogue()).rejects.toThrow();
    expect(new InventoryApiError(503, "INVENTORY_UNCONFIGURED", "Offline").code).toBe("INVENTORY_UNCONFIGURED");
  });
});
