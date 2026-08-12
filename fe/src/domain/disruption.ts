import { z } from "zod";
import { lineGeometrySchema, moneySchema, polygonGeometrySchema, riskLevelSchema } from "./common";
import { facilitySchema } from "./scenario";

export const riskFactorSchema = z.object({ id: z.string(), label: z.string() });
export const roadRiskSchema = z.object({
  segmentId: z.string(), roadName: z.string(),
  highwayClass: z.string().optional(), osmWayIds: z.array(z.string()).default([]),
  geometry: lineGeometrySchema,
  riskProbability: z.number().min(0).max(1), riskLevel: riskLevelSchema,
  estimatedDelayMinutes: z.number().nonnegative(), riskFactors: z.array(riskFactorSchema),
  affectedSupplierIds: z.array(z.string()), affectedWarehouseIds: z.array(z.string()), affectedOrderIds: z.array(z.string()),
});
export const routeSchema = z.object({
  id: z.string(), type: z.enum(["baseline", "recovery"]), originFacilityId: z.string(), destinationFacilityId: z.string(),
  geometry: lineGeometrySchema, distanceKm: z.number().positive(), etaMinutes: z.number().positive(),
  floodExposure: riskLevelSchema, floodExposureProbability: z.number().min(0).max(1), affectedRoadSegmentIds: z.array(z.string()),
});
export const prioritizedIssueSchema = z.object({ id: z.string(), severity: riskLevelSchema, subject: z.string(), description: z.string() });
export const operationalImpactSchema = z.object({
  impactedSupplierIds: z.array(z.string()), impactedWarehouseIds: z.array(z.string()), impactedOrderIds: z.array(z.string()),
  roadSegmentsAtRisk: z.number().int().nonnegative(), salesExposure: moneySchema, issues: z.array(prioritizedIssueSchema),
});
export const disruptionAnalysisSchema = z.object({
  simulationId: z.string(), facilities: z.array(facilitySchema), roads: z.array(roadRiskSchema), routes: z.array(routeSchema),
  historicalFloodGeometry: polygonGeometrySchema.optional(), impact: operationalImpactSchema,
});

export type RiskFactor = z.infer<typeof riskFactorSchema>;
export type RoadRisk = z.infer<typeof roadRiskSchema>;
export type Route = z.infer<typeof routeSchema>;
export type OperationalImpact = z.infer<typeof operationalImpactSchema>;
export type DisruptionAnalysis = z.infer<typeof disruptionAnalysisSchema>;
