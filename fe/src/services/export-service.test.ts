import { describe, expect, it } from "vitest";
import { impactFixture } from "@/mocks/data";
import { impactCsv } from "./export-service";

describe("Impact exports", () => {
  it("includes simulation, business source, recovery status, and KPI values in CSV", () => {
    const data = {
      ...impactFixture,
      recoveryStatus: "no-feasible-plan" as const,
      businessDataSource: "custom" as const,
    };
    const csv = impactCsv(data);

    expect(csv).toContain(`ID Simulasi,${data.simulationId}`);
    expect(csv).toContain("Sumber Data Bisnis,custom");
    expect(csv).toContain("Status Pemulihan,no-feasible-plan");
    expect(csv).toContain("sales-exposure-risk");
  });
});
