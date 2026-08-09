import { z } from "zod";

export const riskLevelSchema = z.enum(["low", "medium", "high", "critical"]);
export type RiskLevel = z.infer<typeof riskLevelSchema>;

const positionSchema = z.tuple([z.number(), z.number()]);

export const geoPointSchema = z.object({ type: z.literal("Point"), coordinates: positionSchema });
export const geoLineSchema = z.object({ type: z.literal("LineString"), coordinates: z.array(positionSchema).min(2) });
export const geoMultiLineSchema = z.object({ type: z.literal("MultiLineString"), coordinates: z.array(z.array(positionSchema).min(2)).min(1) });
export const lineGeometrySchema = z.union([geoLineSchema, geoMultiLineSchema]);
export const geoPolygonSchema = z.object({ type: z.literal("Polygon"), coordinates: z.array(z.array(positionSchema).min(4)).min(1) });
export const geoMultiPolygonSchema = z.object({ type: z.literal("MultiPolygon"), coordinates: z.array(z.array(z.array(positionSchema).min(4)).min(1)).min(1) });
export const polygonGeometrySchema = z.union([geoPolygonSchema, geoMultiPolygonSchema]);

export const moneySchema = z.object({ amount: z.number().nonnegative(), currency: z.literal("IDR") });
export const apiErrorSchema = z.object({
  code: z.string().min(1), message: z.string().min(1), retryable: z.boolean(), details: z.record(z.string(), z.unknown()).optional(),
});
export type ApiErrorPayload = z.infer<typeof apiErrorSchema>;
