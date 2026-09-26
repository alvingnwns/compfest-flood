"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { optimizationPlanService } from "@/services/optimization-plan-service";
import { invalidateInventoryQueries } from "./inventory-query-invalidation";
export const optimizationPlanQueryKey = ["inventory-optimization", "plan"] as const;
export const useOptimizationPlan = () => useQuery({ queryKey: optimizationPlanQueryKey, queryFn: optimizationPlanService.getPlan });
export function usePlanDecision() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (input: { id: string; decision: "APPROVED" | "REJECTED" }) => optimizationPlanService.decide(input.id, input.decision), onSuccess: () => invalidateInventoryQueries(client), onError: () => invalidateInventoryQueries(client) });
}
