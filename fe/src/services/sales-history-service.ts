import { salesHistoryCoverageSchema, salesHistoryImportResponseSchema } from "@/domain/inventory-api";
import { inventoryApiUrl, inventoryRequest, mutationHeaders } from "@/lib/inventory-api";

export const salesHistoryService = {
  templateUrl: inventoryApiUrl("/sales-history/template"),
  getCoverage: () => inventoryRequest("/sales-history/coverage", salesHistoryCoverageSchema),
  importCsv: (file: File, idempotencyKey: string) => {
    const body = new FormData();
    body.append("file", file);
    return inventoryRequest("/sales-history/imports", salesHistoryImportResponseSchema, { method: "POST", body, headers: mutationHeaders(idempotencyKey) });
  },
};
