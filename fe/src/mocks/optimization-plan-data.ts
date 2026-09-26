import type { OptimizationPlan } from "@/domain/optimization-plan";

export const optimizationPlanMock: OptimizationPlan = {
  source: "mock",
  businessDate: "2026-09-27",
  actions: [
    { id: "opt-mango", action: "restock", materialName: "Mangga", quantity: 8, unit: "kg", deadline: "1 Oct 2026", priority: "high", status: "pending", shortage: 4, rationale: "The system detected a 4.0 kg mango shortage risk for this week's operations. Restocking 8.0 kg is recommended to maintain a safe operating level." },
    { id: "opt-avocado", action: "reduce-purchase", materialName: "Alpukat", quantity: 10, unit: "kg", deadline: "3 Oct 2026", priority: "low", status: "pending", shortage: 0, rationale: "Current avocado stock is above forecast demand. Reducing the next purchase by 10.0 kg can limit excess inventory." },
    { id: "opt-orange", action: "restock", materialName: "Jeruk", quantity: 5, unit: "kg", deadline: "2 Oct 2026", priority: "medium", status: "pending", shortage: 2.5, rationale: "Orange stock is approaching the forecast requirement. Restocking 5.0 kg is recommended before the stated deadline." },
  ],
};
