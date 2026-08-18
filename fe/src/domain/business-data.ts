import { z } from "zod";

export const importValidationIssueSchema = z.object({
  sheet: z.string(),
  row: z.number().int().optional(),
  column: z.string().optional(),
  code: z.string(),
  message: z.string(),
});

export const businessSnapshotSummarySchema = z.object({
  productsLoaded: z.number().int().nonnegative(),
  ordersLoaded: z.number().int().nonnegative(),
  inventoryRows: z.number().int().nonnegative(),
  materialsLoaded: z.number().int().nonnegative(),
  bomRelationships: z.number().int().nonnegative(),
  totalOrderValue: z.number().nonnegative(),
  currency: z.literal("IDR"),
});

export const businessImportResponseSchema = z.object({
  valid: z.literal(true),
  businessSnapshotId: z.string(),
  businessDataSource: z.literal("custom"),
  expiresAt: z.iso.datetime({ offset: true }),
  summary: businessSnapshotSummarySchema,
  errors: z.array(importValidationIssueSchema),
});

export type BusinessImportResponse = z.infer<typeof businessImportResponseSchema>;
export type ImportValidationIssue = z.infer<typeof importValidationIssueSchema>;
