import { describe, expect, it } from "vitest";
import { disruptionFixture } from "@/mocks/data";
import {
  BASELINE_ROUTE_COLOR,
  BASELINE_ROUTE_DASHARRAY,
  BASELINE_ROUTE_LABEL,
  CANDIDATE_ROUTE_CASING_COLOR,
  CANDIDATE_ROUTE_COLOR,
  findMatchingRoutesForIssue,
  RISK_AWARE_CANDIDATE_ID_LABEL,
  RISK_AWARE_CANDIDATE_LABEL,
  SELECTED_RECOVERY_ROUTE_LABEL,
  riskAwareCandidateLabel,
} from "./route-semantics";

describe("route semantics & visual hierarchy", () => {
  it("labels pre-optimization routes as candidates, not selected recovery routes", () => {
    expect(riskAwareCandidateLabel("high")).toBe("Risk-Aware Candidate");
    expect(RISK_AWARE_CANDIDATE_LABEL).not.toBe(SELECTED_RECOVERY_ROUTE_LABEL);
    expect(RISK_AWARE_CANDIDATE_ID_LABEL).toBe("Kandidat Risk-Aware");
    expect(BASELINE_ROUTE_LABEL).toBe("Rute Awal");
  });

  it("keeps Critical routes visible only as explicitly Critical candidates", () => {
    expect(riskAwareCandidateLabel("critical")).toBe("Risk-Aware Candidate · Critical exposure");
  });

  it("uses distinct semantic colors for baseline (red), candidate (purple), and casing (white)", () => {
    expect(CANDIDATE_ROUTE_COLOR).toBe("#66558f");
    expect(CANDIDATE_ROUTE_COLOR).not.toBe("#00685f");
    expect(BASELINE_ROUTE_COLOR).toBe("#ba1a1a");
    expect(CANDIDATE_ROUTE_CASING_COLOR).toBe("#ffffff");
    expect(BASELINE_ROUTE_DASHARRAY).toEqual([3, 2]);
  });

  it("matches priority issue by direct route ID or facility pair", () => {
    const issue1 = disruptionFixture.impact.issues[0]; // Pemasok A rute masuk
    const matched1 = findMatchingRoutesForIssue(
      issue1,
      disruptionFixture.routes,
      disruptionFixture.facilities
    );
    expect(matched1.baselineRouteIds).toContain("route-baseline");
    expect(matched1.candidateRouteIds).toContain("route-recovery");

    const issue2 = disruptionFixture.impact.issues[1]; // Gudang Timur → Toko C
    const matched2 = findMatchingRoutesForIssue(
      issue2,
      [
        {
          id: "route-baseline-wh-east-store-c",
          type: "baseline",
          originFacilityId: "wh-east",
          destinationFacilityId: "store-c",
          geometry: { type: "LineString", coordinates: [[106.913, -6.229], [106.893, -6.155]] },
          distanceKm: 12,
          etaMinutes: 20,
          floodExposure: "high",
          floodExposureProbability: 0.8,
          affectedRoadSegmentIds: [],
        },
        {
          id: "route-recovery-wh-east-store-c",
          type: "recovery",
          originFacilityId: "wh-east",
          destinationFacilityId: "store-c",
          geometry: { type: "LineString", coordinates: [[106.913, -6.229], [106.893, -6.155]] },
          distanceKm: 14,
          etaMinutes: 24,
          floodExposure: "low",
          floodExposureProbability: 0.1,
          affectedRoadSegmentIds: [],
        },
      ],
      disruptionFixture.facilities
    );
    expect(matched2.baselineRouteIds).toEqual(["route-baseline-wh-east-store-c"]);
    expect(matched2.candidateRouteIds).toEqual(["route-recovery-wh-east-store-c"]);
  });
});
