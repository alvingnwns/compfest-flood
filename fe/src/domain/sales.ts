import { z } from "zod";

export const salesLineItemSchema = z.object({
  name: z.string().min(1),
  quantity: z.number().int().positive(),
  unitPrice: z.number().nonnegative(),
});

export const inventoryDeductionSchema = z.object({
  materialName: z.string().min(1),
  quantity: z.number().positive(),
  unit: z.string().min(1),
});

export const salesTransactionSchema = z.object({
  id: z.string().min(1),
  occurredAt: z.iso.datetime({ offset: true }),
  cupCount: z.number().int().positive(),
  total: z.number().nonnegative(),
  items: z.array(salesLineItemSchema),
  inventoryDeductions: z.array(inventoryDeductionSchema),
});

export const salesOverviewSchema = z.object({
  source: z.enum(["mock", "api"]),
  businessDate: z.iso.date(),
  summary: z.object({
    revenue: z.number().nonnegative(),
    transactionCount: z.number().int().nonnegative(),
    cupsSold: z.number().int().nonnegative(),
  }),
  transactions: z.array(salesTransactionSchema),
});

export type SalesOverview = z.infer<typeof salesOverviewSchema>;
export type SalesTransaction = z.infer<typeof salesTransactionSchema>;
