import { z } from "zod";
import { apiErrorSchema, riskLevelSchema } from "./common";

const recommendationSchema = z.object({ what: z.string(), why: z.string(), expectedImpact: z.string() });
export const manufacturingActionSchema = recommendationSchema.extend({
  id: z.string(), productId: z.string(), productName: z.string(), baselineQuantity: z.number().nonnegative(), recoveryQuantity: z.number().nonnegative(), changeQuantity: z.number(),
});
export const logisticsActionSchema = recommendationSchema.extend({
  id: z.string(), orderId: z.string(), originalWarehouseId: z.string(), originalWarehouseName: z.string(), recoveryWarehouseId: z.string(), recoveryWarehouseName: z.string(), vehicleId: z.string(),
  baselineRouteId: z.string(), recoveryRouteId: z.string(), baselineEtaMinutes: z.number().nonnegative(), recoveryEtaMinutes: z.number().nonnegative(),
  baselineFloodExposure: riskLevelSchema, recoveryFloodExposure: riskLevelSchema, action: z.enum(["reallocate", "reroute", "reallocate-reroute"]),
});
export const commerceActionSchema = recommendationSchema.extend({
  id: z.string(), orderId: z.string(), storeId: z.string(), storeName: z.string(), requestedProductId: z.string(), requestedProductName: z.string(), requestedQuantity: z.number().positive(),
  action: z.enum(["fulfill", "split", "delay", "substitute", "prioritize", "split-substitute"]),
  allocations: z.array(z.object({ productId: z.string(), productName: z.string(), quantity: z.number().nonnegative() })),
});

const recoveryBaseSchema = z.object({ id: z.string(), simulationId: z.string(), createdAt: z.iso.datetime({ offset: true }) });
const recoveryPendingSchema = recoveryBaseSchema.extend({ status: z.enum(["queued", "processing"]) });
const recoveryFailedSchema = recoveryBaseSchema.extend({ status: z.literal("failed"), error: apiErrorSchema });
const recoveryResultSchema = recoveryBaseSchema.extend({
  status: z.enum(["ready", "partial", "no-feasible-plan"]), completedAt: z.iso.datetime({ offset: true }),
  summary: z.object({ risksMitigated: z.number().int().nonnegative(), operationalChanges: z.number().int().nonnegative(), recoverableOrders: z.number().int().nonnegative(), totalOrders: z.number().int().nonnegative() }),
  manufacturingActions: z.array(manufacturingActionSchema), logisticsActions: z.array(logisticsActionSchema), commerceActions: z.array(commerceActionSchema),
  possibleNextActions: z.array(z.string()),
});
export const recoveryPlanSchema = z.discriminatedUnion("status", [recoveryPendingSchema, recoveryFailedSchema, recoveryResultSchema]);
export const recoveryGenerationRequestSchema = z.object({
  constraints: z.object({ allowSubstitution: z.boolean().optional(), maxAdditionalDelayMinutes: z.number().nonnegative().optional() }).optional(),
});

export type ManufacturingAction = z.infer<typeof manufacturingActionSchema>;
export type LogisticsAction = z.infer<typeof logisticsActionSchema>;
export type CommerceAction = z.infer<typeof commerceActionSchema>;
export type RecoveryPlan = z.infer<typeof recoveryPlanSchema>;
