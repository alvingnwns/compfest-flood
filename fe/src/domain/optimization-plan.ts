import { z } from "zod";

export const optimizationActionSchema = z.object({
  id: z.string().min(1),
  action: z.enum(["restock", "reduce-purchase"]),
  materialName: z.string().min(1),
  quantity: z.number().positive(),
  receivedQuantity: z.number().nonnegative().optional(),
  outstandingQuantity: z.number().nonnegative().optional(),
  planId: z.string().optional(),
  unit: z.string().min(1),
  deadline: z.string().min(1),
  priority: z.enum(["high", "medium", "low"]),
  status: z.enum(["pending", "approved", "completed", "dismissed"]),
  shortage: z.number().nonnegative(),
  rationale: z.string().min(1),
  riskLevel: z.enum(["LOW", "MEDIUM", "HIGH", "STOCKOUT"]).optional(),
  explanationSource: z.enum(["QWEN", "FALLBACK"]).optional(),
  supplierId: z.string().optional(),
  supplierName: z.string().optional(),
  ingredientId: z.string().optional(),
  estimatedCost: z.number().nullable().optional(),
  expectedArrivalAt: z.string().nullable().optional(),
});

export const optimizationPlanSchema = z.object({
  source: z.enum(["mock", "api"]),
  businessDate: z.iso.date(),
  actions: z.array(optimizationActionSchema),
  optimizerStatus: z.string().optional(),
  outcome: z.string().nullable().optional(),
  totalCost: z.number().nullable().optional(),
  limitations: z.array(z.string()).optional(),
});

export type OptimizationAction = z.infer<typeof optimizationActionSchema>;
export type OptimizationPlan = z.infer<typeof optimizationPlanSchema>;
export type OptimizationStatus = OptimizationAction["status"];
