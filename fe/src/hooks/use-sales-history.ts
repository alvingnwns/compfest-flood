"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { salesHistoryService } from "@/services/sales-history-service";
import { invalidateInventoryQueries } from "./inventory-query-invalidation";

export const salesHistoryCoverageQueryKey = ["inventory-sales", "history-coverage"] as const;

export const useSalesHistoryCoverage = (enabled = true) =>
  useQuery({ queryKey: salesHistoryCoverageQueryKey, queryFn: salesHistoryService.getCoverage, enabled });

export const useImportSalesHistory = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, idempotencyKey }: { file: File; idempotencyKey: string }) => salesHistoryService.importCsv(file, idempotencyKey),
    // Imported history changes forecasts, risks and plans, so refresh every inventory view.
    onSuccess: () => invalidateInventoryQueries(client),
  });
};
