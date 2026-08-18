import type { RiskLevel } from "@/domain/common";

export const BASELINE_ROUTE_LABEL = "Baseline Route";
export const RISK_AWARE_CANDIDATE_LABEL = "Risk-Aware Candidate";
export const SELECTED_RECOVERY_ROUTE_LABEL = "Selected Recovery Route";

export const CANDIDATE_ROUTE_COLOR = "#66558f";
export const CANDIDATE_ROUTE_DASHARRAY = [1.5, 1.5];

export function riskAwareCandidateLabel(exposure: RiskLevel): string {
  return exposure === "critical"
    ? `${RISK_AWARE_CANDIDATE_LABEL} · Critical exposure`
    : RISK_AWARE_CANDIDATE_LABEL;
}
