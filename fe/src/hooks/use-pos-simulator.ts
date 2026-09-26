"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { CheckoutRequest } from "@/domain/pos-simulator";
import { posSimulatorService } from "@/services/pos-simulator-service";
import { invalidateInventoryQueries } from "./inventory-query-invalidation";
export const posCatalogueQueryKey = ["inventory", "pos-catalogue"] as const;
export const usePosCatalogue = () => useQuery({ queryKey: posCatalogueQueryKey, queryFn: posSimulatorService.getCatalogue });
export function usePosCheckout() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: CheckoutRequest & { idempotencyKey?: string }) => posSimulatorService.checkout({ items: input.items }, input.idempotencyKey), onSuccess: (result) => result.status === "success" ? invalidateInventoryQueries(client) : undefined });
}
