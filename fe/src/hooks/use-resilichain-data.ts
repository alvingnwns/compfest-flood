"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { analysisService } from "@/services/analysis-service";
import { scenarioService } from "@/services/scenario-service";

const POLL_INTERVAL_MS = 1_000;

export const useScenario = () => useQuery({ queryKey: ["scenario", "historical-jakarta"], queryFn: scenarioService.getHistoricalScenario });
export const useRunSimulation = () => useMutation({ mutationFn: scenarioService.runSimulation });
export const useSimulation = (id: string) => useQuery({
  queryKey: ["simulation", id], queryFn: () => scenarioService.getSimulation(id), enabled: Boolean(id),
  refetchInterval: (query) => ["queued", "processing"].includes(query.state.data?.status ?? "") ? POLL_INTERVAL_MS : false,
});
export const useDisruptionAnalysis = (id: string) => useQuery({ queryKey: ["disruption", id], queryFn: () => analysisService.getDisruption(id), enabled: Boolean(id) });
export const useGenerateRecovery = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, constraints }: { id: string; constraints?: Parameters<typeof analysisService.generateRecovery>[1] }) =>
      analysisService.generateRecovery(id, constraints),
    onSuccess: (_, { id }) => {
      void queryClient.invalidateQueries({ queryKey: ["recovery", id] });
      void queryClient.invalidateQueries({ queryKey: ["impact", id] });
    },
  });
};
export const useRecoveryPlan = (id: string) => useQuery({
  queryKey: ["recovery", id], queryFn: () => analysisService.getRecovery(id), enabled: Boolean(id),
  refetchInterval: (query) => ["queued", "processing"].includes(query.state.data?.status ?? "") ? POLL_INTERVAL_MS : false,
});
export const useImpactComparison = (id: string) => useQuery({ queryKey: ["impact", id], queryFn: () => analysisService.getImpact(id), enabled: Boolean(id) });

