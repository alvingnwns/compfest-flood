import type { RunSimulationRequest } from "@/domain/scenario";
import { runSimulationRequestSchema, scenarioSchema, simulationSchema } from "@/domain/scenario";
import { apiRequest } from "@/lib/api-client";

export const scenarioService = {
  getHistoricalScenario: () => apiRequest("/api/scenarios/historical-jakarta", scenarioSchema),
  runSimulation: (request: RunSimulationRequest) =>
    apiRequest("/api/simulations", simulationSchema, {
      method: "POST",
      body: JSON.stringify(runSimulationRequestSchema.parse(request)),
    }),
  getSimulation: (id: string) => apiRequest(`/api/simulations/${id}`, simulationSchema),
};
