import { disruptionAnalysisSchema } from "@/domain/disruption";
import { impactComparisonSchema } from "@/domain/impact";
import { recoveryGenerationRequestSchema, recoveryPlanSchema } from "@/domain/recovery";
import { apiRequest } from "@/lib/api-client";

export const analysisService = {
  getDisruption: (id: string) => apiRequest(`/api/simulations/${id}/disruption`, disruptionAnalysisSchema),
  generateRecovery: (id: string) => apiRequest(`/api/simulations/${id}/recovery`, recoveryPlanSchema, { method: "POST", body: JSON.stringify(recoveryGenerationRequestSchema.parse({})) }),
  getRecovery: (id: string) => apiRequest(`/api/simulations/${id}/recovery`, recoveryPlanSchema),
  getImpact: (id: string) => apiRequest(`/api/simulations/${id}/impact`, impactComparisonSchema),
};
