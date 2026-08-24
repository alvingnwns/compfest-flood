import { copilotRequestSchema, copilotResponseSchema, type CopilotRequest } from "@/domain/copilot";
import { apiRequest } from "@/lib/api-client";

export const copilotService = {
  ask: (simulationId: string, request: CopilotRequest) =>
    apiRequest(`/api/simulations/${simulationId}/copilot`, copilotResponseSchema, {
      method: "POST",
      body: JSON.stringify(copilotRequestSchema.parse(request)),
    }),
};
