import { optimizationPlanSchema } from "@/domain/optimization-plan";
import { decisionRequestSchema, decisionResponseSchema, procurementResponseSchema } from "@/domain/inventory-api";
import { optimizationPlanMock } from "@/mocks/optimization-plan-data";
import { inventoryRequest, usesInventoryApi, wibDate } from "@/lib/inventory-api";

export const optimizationPlanService = {
  getPlan: async () => {
    if (!usesInventoryApi()) return optimizationPlanSchema.parse(optimizationPlanMock);
    const plan = await inventoryRequest("/procurement/recommendations", procurementResponseSchema);
    return optimizationPlanSchema.parse({ source: "api", businessDate: wibDate(new Date(plan.generatedAt)),
      optimizerStatus: plan.optimizerStatus, outcome: plan.planOutcome, totalCost: plan.totalEstimatedCost, limitations: plan.limitations,
      actions: [...new Map([...plan.recommendations, ...plan.outstandingRecommendations].map((item) => [item.id, item])).values()].map((item) => ({ id: item.id, action: "restock", materialName: item.ingredientName, quantity: item.recommendedOrderQuantity, receivedQuantity: item.receivedQuantity, outstandingQuantity: item.outstandingQuantity, planId: item.planId, unit: item.unit, deadline: item.recommendedOrderAt, priority: item.riskLevel === "STOCKOUT" || item.riskLevel === "HIGH" ? "high" : item.riskLevel === "MEDIUM" ? "medium" : "low", status: item.status === "APPROVED" ? "approved" : item.status === "REJECTED" ? "dismissed" : "pending", shortage: Math.max(0, -item.projectedStock), rationale: item.explanation.text, riskLevel: item.riskLevel, explanationSource: item.explanation.source, ingredientId: item.ingredientId, supplierId: item.supplier.id, supplierName: item.supplier.name, estimatedCost: item.estimatedCost, expectedArrivalAt: item.expectedArrivalAt })),
    });
  },
  decide: async (id: string, decision: "APPROVED" | "REJECTED") => inventoryRequest(`/procurement/recommendations/${encodeURIComponent(id)}/decision`, decisionResponseSchema, { method: "POST", body: JSON.stringify(decisionRequestSchema.parse({ decision })) }),
};
