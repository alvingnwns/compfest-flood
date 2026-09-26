import { z } from "zod";

export const materialStockSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: z.string().min(1),
  quantity: z.number().nonnegative(),
  unit: z.string().min(1),
  reorderLevel: z.number().nonnegative(),
  predictedDemand: z.number().nonnegative(),
  issue: z.enum(["out-of-stock", "low-stock", "shortage-risk", "normal", "surplus"]),
  dueLabel: z.string().min(1),
  stockId: z.string().min(1),
  supplier: z.string().min(1),
  riskReason: z.string().optional(),
  inventoryVersion: z.number().int().nonnegative().optional(),
});

export const stockMovementSchema = z.object({
  id: z.string().min(1),
  materialId: z.string().min(1),
  materialName: z.string().min(1),
  category: z.enum(["Kebutuhan Penjualan", "Stok Masuk", "Rusak", "Penyesuaian", "Terbuang"]),
  quantityChange: z.number(),
  unit: z.string().min(1),
  referenceId: z.string().min(1),
  occurredAt: z.iso.datetime({ offset: true }),
  warningLevel: z.enum(["critical", "warning"]).nullable(),
});

export const inventoryOverviewSchema = z.object({
  source: z.enum(["mock", "api"]),
  businessDate: z.iso.date(),
  materials: z.array(materialStockSchema),
  movements: z.array(stockMovementSchema),
});

export type InventoryOverview = z.infer<typeof inventoryOverviewSchema>;
export type MaterialStock = z.infer<typeof materialStockSchema>;
export type StockMovement = z.infer<typeof stockMovementSchema>;
