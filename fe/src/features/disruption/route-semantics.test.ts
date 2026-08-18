import { describe, expect, it } from "vitest";
import {
  CANDIDATE_ROUTE_COLOR,
  RISK_AWARE_CANDIDATE_LABEL,
  SELECTED_RECOVERY_ROUTE_LABEL,
  riskAwareCandidateLabel,
} from "./route-semantics";

describe("route semantics", () => {
  it("labels pre-optimization routes as candidates, not selected recovery routes", () => {
    expect(riskAwareCandidateLabel("high")).toBe("Risk-Aware Candidate");
    expect(RISK_AWARE_CANDIDATE_LABEL).not.toBe(SELECTED_RECOVERY_ROUTE_LABEL);
  });

  it("keeps Critical routes visible only as explicitly Critical candidates", () => {
    expect(riskAwareCandidateLabel("critical")).toBe("Risk-Aware Candidate · Critical exposure");
  });

  it("uses a candidate color distinct from low-risk and selected-route teal", () => {
    expect(CANDIDATE_ROUTE_COLOR).not.toBe("#00685f");
  });
});
