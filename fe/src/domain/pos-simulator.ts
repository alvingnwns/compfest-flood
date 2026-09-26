import { z } from "zod";

export const posProductSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  materialName: z.string().optional(),
  materialUsageGrams: z.number().positive().optional(),
  price: z.number().nonnegative(),
  availableMaterialGrams: z.number().nonnegative().optional(),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
});

export const posCatalogueSchema = z.object({
  source: z.enum(["mock", "api"]),
  products: z.array(posProductSchema),
  initialOrder: z.array(z.object({ productId: z.string().min(1), quantity: z.number().int().positive() })),
});

export const checkoutRequestSchema = z.object({
  items: z.array(z.object({ productId: z.string().min(1), quantity: z.number().int().positive() })).min(1),
});

export const stockShortageSchema = z.object({
  materialName: z.string().min(1),
  requiredGrams: z.number().positive().optional(),
  availableGrams: z.number().nonnegative().optional(),
  shortageGrams: z.number().positive().optional(),
  required: z.number().optional(),
  available: z.number().optional(),
  shortage: z.number().optional(),
  unit: z.string().optional(),
});

export const checkoutResultSchema = z.discriminatedUnion("status", [
  z.object({ status: z.literal("success"), transactionId: z.string().min(1) }),
  z.object({ status: z.literal("insufficient-stock"), shortages: z.array(stockShortageSchema).min(1) }),
]);

export type PosCatalogue = z.infer<typeof posCatalogueSchema>;
export type PosProduct = z.infer<typeof posProductSchema>;
export type CheckoutRequest = z.infer<typeof checkoutRequestSchema>;
export type CheckoutResult = z.infer<typeof checkoutResultSchema>;
export type StockShortage = z.infer<typeof stockShortageSchema>;
