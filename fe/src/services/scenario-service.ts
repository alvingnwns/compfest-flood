import { runSimulationRequestSchema, scenarioSchema, simulationSchema } from "@/domain/scenario";
import { apiRequest } from "@/lib/api-client";

export const scenarioService = {
  getHistoricalScenario: () => apiRequest("/api/scenarios/historical-jakarta", scenarioSchema),
  runSimulation: (scenarioId: string) => apiRequest("/api/simulations", simulationSchema, { method: "POST", body: JSON.stringify(runSimulationRequestSchema.parse({ scenarioId })) }),
  getSimulation: (id: string) => apiRequest(`/api/simulations/${id}`, simulationSchema),
};
