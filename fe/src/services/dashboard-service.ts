import { dashboardSummarySchema } from "@/domain/dashboard";
import { dashboardResponseSchema } from "@/domain/inventory-api";
import { dashboardSummaryMock } from "@/mocks/dashboard-data";
import { inventoryRequest, usesInventoryApi } from "@/lib/inventory-api";
import { riskStatus } from "@/lib/inventory-risk";
import { getRisks, getProducts, getForecast } from "./inventory-api-data";

export const dashboardService = {
  getSummary: async () => {
    if (!usesInventoryApi()) return dashboardSummarySchema.parse(dashboardSummaryMock);
    const summary = await inventoryRequest("/dashboard/summary", dashboardResponseSchema);
    const [risks, products] = await Promise.all([getRisks(), getProducts()]);
    const forecasts = await Promise.all(products.map((product) => getForecast(product.id)));
    const projection = new Map<string, { label: string; actual: number | null; predicted: number | null }>();
    for (const forecast of forecasts) {
      for (const point of forecast.history.slice(-3)) {
        const row = projection.get(point.date) ?? { label: point.date, actual: null, predicted: null };
        row.actual = (row.actual ?? 0) + point.actualDemand; projection.set(point.date, row);
      }
      for (const point of forecast.forecast) {
        const row = projection.get(point.date) ?? { label: point.date, actual: null, predicted: null };
        row.predicted = (row.predicted ?? 0) + point.predictedDemand; projection.set(point.date, row);
      }
    }
    return dashboardSummarySchema.parse({
      source: "api",
      hasInventoryData: risks.items.length > 0,
      forecastSources: [...new Set(forecasts.map((forecast) => forecast.source ?? "UNKNOWN"))],
      historySources: [...new Set(forecasts.flatMap((forecast) => forecast.history.slice(-3).map((point) => point.historySource ?? "UNKNOWN")))],
      trainingDataSynthetic: forecasts.some((forecast) => forecast.trainingDataSynthetic === true) ? true : forecasts.length > 0 && forecasts.every((forecast) => forecast.trainingDataSynthetic === false) ? false : null,
      metrics: [
        { id: "gross-sales", label: "Gross Sales", value: summary.today.revenue, format: "currency" },
        { id: "products-sold", label: "Products Sold", value: summary.today.productsSold, format: "number" },
        { id: "at-risk-materials", label: "At-Risk Materials", value: summary.inventory.atRiskIngredientCount, format: "number" },
        { id: "pending-actions", label: "Pending Actions", value: summary.inventory.activeRecommendationCount, format: "number" },
      ],
      inventoryRisks: risks.items.filter((risk) => risk.riskLevel !== "LOW").map((risk) => ({
        id: risk.ingredientId, materialName: risk.ingredientName, availableQuantity: risk.currentStock,
        predictedDemand: risk.predictedRequirement, unit: risk.unit, status: riskStatus(risk.riskLevel),
        statusLabel: risk.riskLevel, dueLabel: risk.projectedStockoutDate ?? "—",
      })),
      priorityRecommendations: summary.priorityActions.map((item) => ({ id: item.recommendationId, title: `Order ${item.recommendedOrderQuantity} ${item.unit} ${item.ingredientName}`, detail: item.summary, materialName: item.ingredientName, quantity: item.recommendedOrderQuantity, unit: item.unit })),
      demandProjection: [...projection.values()].sort((a, b) => a.label.localeCompare(b.label)),
    });
  },
};
