import type { RiskLevel } from "@/domain/common";
import type { PrioritizedIssue, Route } from "@/domain/disruption";
import type { Facility } from "@/domain/scenario";

export const BASELINE_ROUTE_LABEL = "Rute Awal";
export const RISK_AWARE_CANDIDATE_LABEL = "Risk-Aware Candidate";
export const RISK_AWARE_CANDIDATE_ID_LABEL = "Kandidat Risk-Aware";
export const SELECTED_RECOVERY_ROUTE_LABEL = "Selected Recovery Route";

export const BASELINE_ROUTE_COLOR = "#ba1a1a";
export const BASELINE_ROUTE_DASHARRAY = [3, 2];
export const CANDIDATE_ROUTE_COLOR = "#66558f";
export const CANDIDATE_ROUTE_CASING_COLOR = "#ffffff";

export function riskAwareCandidateLabel(exposure: RiskLevel): string {
  return exposure === "critical"
    ? `${RISK_AWARE_CANDIDATE_LABEL} · Critical exposure`
    : RISK_AWARE_CANDIDATE_LABEL;
}

export type MatchedIssueRoutes = {
  baselineRouteIds: string[];
  candidateRouteIds: string[];
  allMatchedRouteIds: string[];
  originFacilityId?: string;
  destinationFacilityId?: string;
};

export function findMatchingRoutesForIssue(
  issue: PrioritizedIssue,
  routes: Route[],
  facilities: Facility[] = []
): MatchedIssueRoutes {
  const strippedId = issue.id.replace(/^issue-/, "");

  // 1. Direct route ID match (e.g., issue-route-baseline-wh-east-store-c or route-baseline)
  const directRoute = routes.find(
    (r) => r.id === strippedId || strippedId === r.id || strippedId.endsWith(r.id) || r.id.endsWith(strippedId)
  );

  if (directRoute) {
    const pairRoutes = routes.filter(
      (r) =>
        (r.originFacilityId === directRoute.originFacilityId &&
          r.destinationFacilityId === directRoute.destinationFacilityId) ||
        r.id === directRoute.id
    );
    const baselineRouteIds = pairRoutes.filter((r) => r.type === "baseline").map((r) => r.id);
    const candidateRouteIds = pairRoutes.filter((r) => r.type === "recovery").map((r) => r.id);
    return {
      baselineRouteIds,
      candidateRouteIds,
      allMatchedRouteIds: [...baselineRouteIds, ...candidateRouteIds],
      originFacilityId: directRoute.originFacilityId,
      destinationFacilityId: directRoute.destinationFacilityId,
    };
  }

  const lowerSubject = issue.subject.toLowerCase();
  const lowerDesc = issue.description.toLowerCase();
  const fullText = `${lowerSubject} ${lowerDesc}`;

  // 2. Check facility names mentioned in subject / description
  const mentionedFacilities = facilities.filter(
    (f) =>
      lowerSubject.includes(f.name.toLowerCase()) ||
      lowerSubject.includes(f.id.toLowerCase()) ||
      lowerDesc.includes(f.name.toLowerCase()) ||
      lowerDesc.includes(f.id.toLowerCase())
  );

  if (mentionedFacilities.length >= 2) {
    // Sort by order of appearance in subject/description to determine origin vs destination
    const sorted = [...mentionedFacilities].sort((a, b) => {
      const idxA = fullText.indexOf(a.name.toLowerCase());
      const idxB = fullText.indexOf(b.name.toLowerCase());
      return (idxA >= 0 ? idxA : 9999) - (idxB >= 0 ? idxB : 9999);
    });
    const origin = sorted[0];
    const dest = sorted[1];

    const pairRoutes = routes.filter(
      (r) =>
        (r.originFacilityId === origin.id && r.destinationFacilityId === dest.id) ||
        (r.originFacilityId === dest.id && r.destinationFacilityId === origin.id)
    );

    if (pairRoutes.length > 0) {
      const baselineRouteIds = pairRoutes.filter((r) => r.type === "baseline").map((r) => r.id);
      const candidateRouteIds = pairRoutes.filter((r) => r.type === "recovery").map((r) => r.id);
      return {
        baselineRouteIds,
        candidateRouteIds,
        allMatchedRouteIds: [...baselineRouteIds, ...candidateRouteIds],
        originFacilityId: origin.id,
        destinationFacilityId: dest.id,
      };
    }
  }

  if (mentionedFacilities.length === 1) {
    const single = mentionedFacilities[0];
    const connectedRoutes = routes.filter(
      (r) => r.originFacilityId === single.id || r.destinationFacilityId === single.id
    );
    if (connectedRoutes.length > 0) {
      const baselineRouteIds = connectedRoutes.filter((r) => r.type === "baseline").map((r) => r.id);
      const candidateRouteIds = connectedRoutes.filter((r) => r.type === "recovery").map((r) => r.id);
      return {
        baselineRouteIds,
        candidateRouteIds,
        allMatchedRouteIds: [...baselineRouteIds, ...candidateRouteIds],
        originFacilityId: single.id,
      };
    }
  }

  // 3. Fallback: match by facility IDs directly inside strippedId or subject
  const partialMatches = routes.filter(
    (r) =>
      strippedId.includes(r.originFacilityId) ||
      strippedId.includes(r.destinationFacilityId) ||
      lowerSubject.includes(r.originFacilityId.toLowerCase()) ||
      lowerSubject.includes(r.destinationFacilityId.toLowerCase())
  );

  const baselineRouteIds = partialMatches.filter((r) => r.type === "baseline").map((r) => r.id);
  const candidateRouteIds = partialMatches.filter((r) => r.type === "recovery").map((r) => r.id);

  return {
    baselineRouteIds,
    candidateRouteIds,
    allMatchedRouteIds: [...baselineRouteIds, ...candidateRouteIds],
  };
}
