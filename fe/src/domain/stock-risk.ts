import { z } from "zod";

export const stockRiskMaterialSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  currentStock: z.number().nonnegative(),
  predictedNeed: z.number().nonnegative(),
  unit: z.string().min(1),
  difference: z.number(),
  status: z.enum(["out-of-stock", "low-stock", "shortage-risk", "surplus", "normal"]),
  restockLeadTime: z.string().min(1),
  riskReason: z.string().optional(),
});

export const stockRiskOverviewSchema = z.object({
  source: z.enum(["mock", "api"]),
  businessDate: z.iso.date(),
  materials: z.array(stockRiskMaterialSchema),
});

export type StockRiskMaterial = z.infer<typeof stockRiskMaterialSchema>;
export type StockRiskOverview = z.infer<typeof stockRiskOverviewSchema>;
