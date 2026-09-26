import { z } from "zod";

export const demandForecastPointSchema = z.object({
  label: z.string().min(1),
  actual: z.number().nonnegative().nullable(),
  historySource: z.string().nullable().optional(),
  predicted: z.number().nonnegative().nullable(),
});

export const demandForecastDetailSchema = z.object({
  dateLabel: z.string().min(1),
  productName: z.string().min(1),
  predictedSales: z.number().int().nonnegative(),
  primaryMaterial: z.string().min(1).optional(),
  estimatedRequirement: z.number().nonnegative().optional(),
  unit: z.string().min(1).optional(),
});

export const demandForecastSchema = z.object({
  source: z.enum(["mock", "api"]),
  productId: z.string(),
  productName: z.string(),
  horizonDays: z.number().int().positive(),
  totalPredictedSales: z.number().int().nonnegative(),
  points: z.array(demandForecastPointSchema),
  details: z.array(demandForecastDetailSchema),
  products: z.array(z.object({ id: z.string(), name: z.string() })).optional(),
  modelLabel: z.string().optional(),
  synthetic: z.boolean().optional(),
  forecastSource: z.enum(["XGBOOST", "FALLBACK"]).nullable().optional(),
  trainingDataSynthetic: z.boolean().nullable().optional(),
  fallbackReason: z.string().nullable().optional(),
  requirements: z.array(z.object({ name: z.string(), quantity: z.number(), unit: z.string() })).optional(),
}).refine((data) => {
  if (data.productId === "" || data.productName === "") {
    return data.productId === "" && data.productName === "" && data.products?.length === 0 &&
      data.points.length === 0 && data.details.length === 0 && data.totalPredictedSales === 0;
  }
  return data.details.length === 0 || data.points.length >= 2;
}, { message: "Forecast must identify a product, or represent an empty catalogue." });

export type DemandForecast = z.infer<typeof demandForecastSchema>;
