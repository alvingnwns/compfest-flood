"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { inventoryService } from "@/services/inventory-service";
import { invalidateInventoryQueries } from "./inventory-query-invalidation";
export const inventoryOverviewQueryKey = ["inventory", "overview"] as const;
export const useInventoryOverview = () => useQuery({ queryKey: inventoryOverviewQueryKey, queryFn: inventoryService.getOverview });
export const useReceivingSuppliers = (enabled: boolean) => useQuery({ queryKey: ["inventory", "receiving-suppliers"], queryFn: inventoryService.getSuppliers, enabled });
export function useStockMutation() {
  const client = useQueryClient();
  return useMutation({ mutationFn: async (input: { id: string; mode: "adjust" | "receive"; payload: unknown; key: string }) => {
    const result = input.mode === "adjust" ? await inventoryService.adjust(input.id, input.payload, input.key) : await inventoryService.receive(input.id, input.payload, input.key);
    return result.inventory;
  }, onSuccess: () => invalidateInventoryQueries(client), onError: () => invalidateInventoryQueries(client) });
}
