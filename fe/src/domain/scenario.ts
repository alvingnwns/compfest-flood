import { z } from "zod";
import { apiErrorSchema, geoPointSchema } from "./common";

export const facilityKindSchema = z.enum(["supplier", "factory", "warehouse", "store"]);
export const facilitySchema = z.object({ id: z.string(), name: z.string(), kind: facilityKindSchema, location: geoPointSchema });
export const vehicleSchema = z.object({ id: z.string(), label: z.string(), capacityUnits: z.number().int().positive() });
export const productSchema = z.object({ id: z.string(), name: z.string(), unit: z.string() });
export const materialSchema = z.object({ id: z.string(), name: z.string(), supplierId: z.string(), productIds: z.array(z.string()).min(1) });
export const inventorySchema = z.object({ facilityId: z.string(), productId: z.string(), quantity: z.number().nonnegative(), unit: z.string() });
export const orderSchema = z.object({
  id: z.string(), storeId: z.string(), productId: z.string(), quantity: z.number().int().positive(), priority: z.enum(["normal", "high", "critical"]),
});

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

export const simulationSchema = z.object({
  id: z.string(), scenarioId: z.string(), status: simulationStatusSchema, createdAt: z.iso.datetime({ offset: true }),
  completedAt: z.iso.datetime({ offset: true }).optional(), modelVersion: z.string().optional(), modelProvenance: modelProvenanceSchema.optional(), optimizerVersion: z.string().optional(),
  dataMode: dataSourceModeSchema, historicalDataStatus: historicalDataStatusSchema, error: apiErrorSchema.optional(),
});
export const runSimulationRequestSchema = z.object({ scenarioId: z.string().min(1) });

export type Scenario = z.infer<typeof scenarioSchema>;
export type Facility = z.infer<typeof facilitySchema>;
export type Vehicle = z.infer<typeof vehicleSchema>;
export type Product = z.infer<typeof productSchema>;
export type Material = z.infer<typeof materialSchema>;
export type Inventory = z.infer<typeof inventorySchema>;
export type Order = z.infer<typeof orderSchema>;
export type Simulation = z.infer<typeof simulationSchema>;
