import { z } from "zod";

const facilityKindSchema = z.enum(["supplier", "factory", "warehouse", "store"]);
const positionSchema = z.tuple([z.number(), z.number()]);
const geoPointSchema = z.object({ type: z.literal("Point"), coordinates: positionSchema });
const facilitySchema = z.object({ id: z.string(), name: z.string(), kind: facilityKindSchema, location: geoPointSchema });
const vehicleSchema = z.object({ id: z.string(), label: z.string(), capacityUnits: z.number().int().positive() });
const productSchema = z.object({ id: z.string(), name: z.string(), unit: z.string() });
const materialSchema = z.object({ id: z.string(), name: z.string(), supplierId: z.string(), productIds: z.array(z.string()).min(1) });
const inventorySchema = z.object({ facilityId: z.string(), productId: z.string(), quantity: z.number().nonnegative(), unit: z.string() });
const orderSchema = z.object({
  id: z.string(), storeId: z.string(), productId: z.string(), quantity: z.number().int().positive(), priority: z.enum(["normal", "high", "critical"]),
});

const dataSourceModeSchema = z.enum(["historical_snapshot", "live", "hybrid"]);
const historicalDataStatusSchema = z.enum(["available", "offline_snapshot", "unavailable"]);
const operationalDataStatusSchema = z.enum(["simulated", "live"]);
const dataSourcesSchema = z.object({
  mode: dataSourceModeSchema,
  historicalStatus: historicalDataStatusSchema,
  operationalStatus: operationalDataStatusSchema,
  historicalProvider: z.string(),
  snapshotId: z.string().optional(),
});

const scenarioSchema = z.object({
  id: z.string(), name: z.string(), mode: z.literal("historical-replay"), location: z.string(), eventDate: z.string(), eventType: z.string(),
  dataSources: dataSourcesSchema, companyName: z.string(), facilities: z.array(facilitySchema), vehicles: z.array(vehicleSchema),
  products: z.array(productSchema), materials: z.array(materialSchema), inventory: z.array(inventorySchema), orders: z.array(orderSchema),
});

async function main() {
  try {
    console.log("Fetching scenario...");
    const res = await fetch("http://localhost:8000/api/scenarios/historical-jakarta");
    if (!res.ok) {
        console.log("API Error:", res.status, res.statusText);
        return;
    }
    const data = await res.json();
    console.log("Parsing schema...");
    scenarioSchema.parse(data);
    console.log("SUCCESS");
  } catch (err) {
    if (err instanceof z.ZodError) {
      console.log(JSON.stringify(err.issues, null, 2));
    } else {
      console.error(err);
    }
  }
}
main();
