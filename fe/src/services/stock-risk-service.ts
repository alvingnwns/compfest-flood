import { stockRiskOverviewSchema } from "@/domain/stock-risk";
import { stockRiskOverviewMock } from "@/mocks/stock-risk-data";
import { usesInventoryApi, wibDate } from "@/lib/inventory-api";
import { riskStatus } from "@/lib/inventory-risk";
import { getRisks } from "./inventory-api-data";

export const stockRiskService = {
  getOverview: async () => {
    if (!usesInventoryApi()) return stockRiskOverviewSchema.parse(stockRiskOverviewMock);
    const risks = await getRisks();
    return stockRiskOverviewSchema.parse({ source: "api", businessDate: wibDate(new Date(risks.generatedAt)), materials: risks.items.map((item) => ({ id: item.ingredientId, name: item.ingredientName, currentStock: item.currentStock, predictedNeed: item.predictedRequirement, unit: item.unit, difference: item.projectedStock, status: riskStatus(item.riskLevel), restockLeadTime: `${item.leadTimeHours} h`, riskReason: item.riskReason })) });
  },
};
