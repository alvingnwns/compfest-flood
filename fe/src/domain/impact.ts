import { z } from "zod";

const metricBase = { baseline: z.number().nonnegative(), recovery: z.number().nonnegative() };
export const impactMetricSchema = z.discriminatedUnion("key", [
  z.object({ key: z.literal("orders-fulfilled"), ...metricBase, total: z.number().int().positive() }),
  z.object({ key: z.literal("on-time-delivery"), baseline: z.number().min(0).max(1), recovery: z.number().min(0).max(1) }),
  z.object({ key: z.literal("failed-orders"), baseline: z.number().int().nonnegative(), recovery: z.number().int().nonnegative() }),
  z.object({
    key: z.literal("average-delay"),
    ...metricBase,
    baselineObservationCount: z.number().int().nonnegative(),
    recoveryObservationCount: z.number().int().nonnegative(),
  }),
  z.object({ key: z.literal("sales-exposure-risk"), ...metricBase, currency: z.literal("IDR") }),
]);
export const impactComparisonSchema = z.object({
  simulationId: z.string(),
  recoveryStatus: z.enum(["ready", "partial", "no-feasible-plan"]),
  businessDataSource: z.enum(["demo", "custom"]),
  metrics: z.array(impactMetricSchema).length(5),
  actionCounts: z.object({ manufacturing: z.number().int().nonnegative(), logistics: z.number().int().nonnegative(), commerce: z.number().int().nonnegative() }),
}).superRefine((value, context) => {
  const keys = new Set(value.metrics.map((metric) => metric.key));
  if (keys.size !== value.metrics.length) context.addIssue({ code: "custom", path: ["metrics"], message: "Impact metric keys must be unique" });
});

export type ImpactMetric = z.infer<typeof impactMetricSchema>;
export type ImpactComparison = z.infer<typeof impactComparisonSchema>;
