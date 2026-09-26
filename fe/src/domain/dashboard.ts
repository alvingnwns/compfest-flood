import { z } from "zod";

export const dashboardMetricSchema = z.object({
  id: z.enum(["gross-sales", "products-sold", "at-risk-materials", "pending-actions"]),
  label: z.string().min(1),
  value: z.number().nonnegative(),
  format: z.enum(["currency", "number"]),
});

export const inventoryRiskSchema = z.object({
  id: z.string().min(1),
  materialName: z.string().min(1),
  availableQuantity: z.number().nonnegative(),
  predictedDemand: z.number().nonnegative(),
  unit: z.string().min(1),
  status: z.enum(["out-of-stock", "low-stock", "shortage-risk", "expiring", "surplus"]),
  statusLabel: z.string().min(1),
  dueLabel: z.string().min(1),
});

export const priorityRecommendationSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  detail: z.string().min(1),
  materialName: z.string().optional(),
  quantity: z.number().optional(),
  unit: z.string().optional(),
});

export const demandProjectionPointSchema = z.object({
  label: z.string().min(1),
  actual: z.number().nonnegative().nullable(),
  predicted: z.number().nonnegative().nullable(),
});

export const dashboardSummarySchema = z.object({
  source: z.enum(["mock", "api"]),
  hasInventoryData: z.boolean().optional(),
  metrics: z.array(dashboardMetricSchema).length(4),
  inventoryRisks: z.array(inventoryRiskSchema),
  priorityRecommendations: z.array(priorityRecommendationSchema),
  demandProjection: z.array(demandProjectionPointSchema),
  forecastSources: z.array(z.string()).optional(),
  historySources: z.array(z.string()).optional(),
  trainingDataSynthetic: z.boolean().nullable().optional(),
});

export type DashboardSummary = z.infer<typeof dashboardSummarySchema>;
export type InventoryRisk = z.infer<typeof inventoryRiskSchema>;
export type InventoryRiskStatus = InventoryRisk["status"];
