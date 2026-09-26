import { describe, expect, it } from "vitest";
import { dashboardService } from "./dashboard-service";
import { salesService } from "./sales-service";
import { inventoryService } from "./inventory-service";
import { demandForecastService } from "./demand-forecast-service";
import { stockRiskService } from "./stock-risk-service";
import { optimizationPlanService } from "./optimization-plan-service";
import { posSimulatorService } from "./pos-simulator-service";
import { inventoryRequest } from "@/lib/inventory-api";
import { transactionResponseSchema } from "@/domain/inventory-api";

// Explicit read-only smoke test against the configured local backend.
describe.skipIf(process.env.ARUNA_API_SMOKE !== "1")("live inventory service adapters", () => {
  it("validates and maps all seven page responses from the running backend", async () => {
    const catalogue = await posSimulatorService.getCatalogue();
    expect(catalogue.source).toBe("api");
    expect(catalogue.products.length).toBeGreaterThan(0);
    const forecast = await demandForecastService.getForecast(catalogue.products[0].id);
    expect(forecast.source).toBe("api");
    expect(forecast.totalPredictedSales).toBe(forecast.details.reduce((sum, row) => sum + row.predictedSales, 0));
    const inventory = await inventoryService.getOverview();
    const risks = await stockRiskService.getOverview();
    const sales = await salesService.getOverview();
    const plan = await optimizationPlanService.getPlan();
    const dashboard = await dashboardService.getSummary();
    for (const data of [inventory, risks, sales, plan, dashboard]) expect(data.source).toBe("api");
    expect(dashboard.metrics.find((metric) => metric.id === "gross-sales")?.value).toBe(sales.summary.revenue);
    expect(risks.materials.length).toBe(inventory.materials.length);
  }, 90000);

  it.skipIf(process.env.ARUNA_API_MUTATION_SMOKE !== "1")("persists checkout once, updates Sales and Inventory, then voids the verification sale", async () => {
    const catalogue = await posSimulatorService.getCatalogue();
    const before = await inventoryService.getOverview();
    const key = `frontend-verification-${crypto.randomUUID()}`;
    const order = { items: [{ productId: catalogue.products[0].id, quantity: 1 }] };
    let transactionId: string | undefined;
    try {
      const result = await posSimulatorService.checkout(order, key);
      expect(result.status).toBe("success");
      if (result.status !== "success") throw new Error("Verification checkout did not complete");
      transactionId = result.transactionId;
      const repeat = await posSimulatorService.checkout(order, key);
      expect(repeat).toEqual(result);
      const detail = await salesService.getTransaction(transactionId);
      expect(detail?.inventoryDeductions.length).toBeGreaterThan(0);
      const sales = await salesService.getOverview();
      expect(sales.transactions.some((transaction) => transaction.id === transactionId)).toBe(true);
      const after = await inventoryService.getOverview();
      for (const consumption of detail!.inventoryDeductions) {
        const original = before.materials.find((item) => item.name === consumption.materialName)!;
        const updated = after.materials.find((item) => item.id === original.id)!;
        expect(updated.quantity).toBeCloseTo(original.quantity - consumption.quantity, 6);
      }
    } finally {
      if (transactionId) await inventoryRequest(`/transactions/${encodeURIComponent(transactionId)}/void`, transactionResponseSchema, { method: "POST", body: JSON.stringify({ reason: "Frontend integration verification: restore stock after smoke test" }) });
    }
    const restored = await inventoryService.getOverview();
    for (const original of before.materials) expect(restored.materials.find((item) => item.id === original.id)?.quantity).toBeCloseTo(original.quantity, 6);
  }, 90000);
});
