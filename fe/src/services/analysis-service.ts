import { disruptionAnalysisSchema } from "@/domain/disruption";
import { impactComparisonSchema } from "@/domain/impact";
import { recoveryGenerationRequestSchema, recoveryPlanSchema } from "@/domain/recovery";
import type { z } from "zod";
import { apiRequest } from "@/lib/api-client";

type RecoveryConstraints = z.infer<typeof recoveryGenerationRequestSchema>["constraints"];

export const analysisService = {
  getDisruption: (id: string) => apiRequest(`/api/simulations/${id}/disruption`, disruptionAnalysisSchema),
  generateRecovery: (id: string, constraints?: RecoveryConstraints) =>
    apiRequest(`/api/simulations/${id}/recovery`, recoveryPlanSchema, {
      method: "POST",
      body: JSON.stringify(recoveryGenerationRequestSchema.parse({ constraints })),
    }),
  getRecovery: (id: string) => apiRequest(`/api/simulations/${id}/recovery`, recoveryPlanSchema),
  getImpact: (id: string) => apiRequest(`/api/simulations/${id}/impact`, impactComparisonSchema),
};

