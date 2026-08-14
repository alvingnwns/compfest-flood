import { z } from "zod";
import { apiErrorSchema, geoPointSchema } from "./common";

export const facilityKindSchema = z.enum(["supplier", "factory", "warehouse", "store"]);
export const facilitySchema = z.object({ id: z.string(), name: z.string(), kind: facilityKindSchema, location: geoPointSchema });
export const vehicleSchema = z.object({ id: z.string(), label: z.string(), capacityUnits: z.number().int().positive(), available: z.boolean().optional().default(true) });
export const productSchema = z.object({ id: z.string(), name: z.string(), unit: z.string() });
export const materialSchema = z.object({ id: z.string(), name: z.string(), supplierId: z.string(), productIds: z.array(z.string()).min(1) });
export const inventorySchema = z.object({ facilityId: z.string(), productId: z.string(), quantity: z.number().nonnegative(), unit: z.string() });
export const orderSchema = z.object({
  id: z.string(), storeId: z.string(), productId: z.string(), quantity: z.number().int().positive(), priority: z.enum(["normal", "high", "critical"]),
});

export const vehicleOverrideSchema = z.object({
  id: z.string(),
  available: z.boolean().optional(),
  capacityUnits: z.number().int().positive().optional(),
});
export const inventoryOverrideSchema = z.object({
  facilityId: z.string(),
  productId: z.string(),
  quantity: z.number().nonnegative(),
});
export const analysisModeSchema = z.enum(["historical-replay", "scenario-simulation"]);
export const regionSchema = z.literal("jakarta");
export const rainfallScenarioSchema = z.enum(["Q1", "Q2", "Q3", "Q4"]);
const runSimulationRequestBaseSchema = z.object({
  scenarioId: z.string().min(1),
  vehicleOverrides: z.array(vehicleOverrideSchema).optional(),
  inventoryOverrides: z.array(inventoryOverrideSchema).optional(),
});
export const runSimulationRequestSchema = z.union([
  runSimulationRequestBaseSchema.extend({
    analysisMode: z.literal("scenario-simulation"),
    region: regionSchema,
    rainfallScenario: rainfallScenarioSchema,
  }),
  runSimulationRequestBaseSchema.extend({
    analysisMode: z.literal("historical-replay").default("historical-replay"),
    region: regionSchema.optional(),
    rainfallScenario: rainfallScenarioSchema.optional(),
  }),
]);

export const dataSourceModeSchema = z.enum(["historical_snapshot", "live", "hybrid"]);
export const historicalDataStatusSchema = z.enum(["available", "offline_snapshot", "unavailable"]);
export const operationalDataStatusSchema = z.enum(["simulated", "live"]);
export const dataSourcesSchema = z.object({
  mode: dataSourceModeSchema,
  historicalStatus: historicalDataStatusSchema,
  operationalStatus: operationalDataStatusSchema,
  historicalProvider: z.string(),
  snapshotId: z.string().optional(),
});

export const scenarioSchema = z.object({
  id: z.string(), name: z.string(), mode: z.literal("historical-replay"), location: z.string(), eventDate: z.iso.date(), eventType: z.string(),
  dataSources: dataSourcesSchema, companyName: z.string(), facilities: z.array(facilitySchema), vehicles: z.array(vehicleSchema),
  products: z.array(productSchema), materials: z.array(materialSchema), inventory: z.array(inventorySchema), orders: z.array(orderSchema),
});

export const simulationStatusSchema = z.enum(["queued", "processing", "completed", "failed"]);
export const modelProvenanceSchema = z.object({
  trainingData: z.string(),
  source: z.string(),
  target: z.string(),
  algorithm: z.string(),
  trainingScope: z.string(),
  deploymentScope: z.string(),
  trainingEvents: z.number().int().positive(),
  trainingRegions: z.number().int().positive(),
  jakartaValidationStatus: z.enum(["not_validated", "validated"]),
  probabilitySemantics: z.string(),
});
export const dynamicHazardMetadataSchema = z.object({
  rainfallScenario: rainfallScenarioSchema,
  temporalHazardScore: z.number().min(0).max(1),
  relativeHazardIndex: z.number().min(0).max(1),
  probabilityCalibrated: z.literal(false),
  modelVersion: z.string(),
  modelType: z.string(),
  fusionMethod: z.literal("logit_shift"),
  fusionBeta: z.number(),
  riskLevelSemantics: z.string(),
});

export const simulationSchema = z.object({
  id: z.string(), scenarioId: z.string(), status: simulationStatusSchema, createdAt: z.iso.datetime({ offset: true }),
  completedAt: z.iso.datetime({ offset: true }).optional(), modelVersion: z.string().optional(), modelProvenance: modelProvenanceSchema.optional(), optimizerVersion: z.string().optional(),
  dataMode: dataSourceModeSchema, historicalDataStatus: historicalDataStatusSchema, error: apiErrorSchema.optional(),
  analysisMode: analysisModeSchema.default("historical-replay"), region: regionSchema.default("jakarta"),
  hazard: dynamicHazardMetadataSchema.optional(),
}).superRefine((value, context) => {
  if (value.analysisMode === "scenario-simulation" && value.hazard === undefined) {
    context.addIssue({ code: "custom", path: ["hazard"], message: "Metadata hazard wajib tersedia untuk simulasi kondisi." });
  }
  if (value.analysisMode === "historical-replay" && value.hazard !== undefined) {
    context.addIssue({ code: "custom", path: ["hazard"], message: "Metadata hazard dinamis tidak berlaku untuk replay historis." });
  }
});

export type Scenario = z.infer<typeof scenarioSchema>;
export type Facility = z.infer<typeof facilitySchema>;
export type Vehicle = z.infer<typeof vehicleSchema>;
export type Product = z.infer<typeof productSchema>;
export type Material = z.infer<typeof materialSchema>;
export type Inventory = z.infer<typeof inventorySchema>;
export type Order = z.infer<typeof orderSchema>;
export type Simulation = z.infer<typeof simulationSchema>;
export type VehicleOverride = z.infer<typeof vehicleOverrideSchema>;
export type InventoryOverride = z.infer<typeof inventoryOverrideSchema>;
export type RunSimulationRequest = z.infer<typeof runSimulationRequestSchema>;
export type AnalysisMode = z.infer<typeof analysisModeSchema>;
export type RainfallScenario = z.infer<typeof rainfallScenarioSchema>;
