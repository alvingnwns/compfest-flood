import { describe, expect, it } from "vitest";
import { disruptionAnalysisSchema } from "./disruption";
import { impactComparisonSchema } from "./impact";
import { recoveryPlanSchema } from "./recovery";
import { scenarioSchema, simulationSchema } from "./scenario";
import { disruptionFixture, impactFixture, recoveryFixture, scenarioFixture, simulationFixture } from "@/mocks/data";

describe("API contract examples", () => {
  it("parses the coherent scenario and simulation fixtures", () => {
    const result = scenarioSchema.parse(scenarioFixture);
    expect(result.orders).toHaveLength(20);
    expect(result.inventory.length).toBeGreaterThan(0);
    expect(result.facilities.filter((item) => item.kind === "supplier")).toHaveLength(2);
    expect(simulationSchema.parse(simulationFixture).status).toBe("completed");
    const provenance = simulationSchema.parse(simulationFixture).modelProvenance;
    expect(provenance?.trainingData).toBe("real-historical-global-flood-database-indonesia");
    expect(provenance?.jakartaValidationStatus).toBe("not_validated");
  });

  it("parses disruption, recovery, and impact responses", () => {
    expect(disruptionAnalysisSchema.parse(disruptionFixture).roads[0].riskProbability).toBe(0.82);
    const recovery = recoveryPlanSchema.parse(recoveryFixture);
    expect(recovery.status === "ready" || recovery.status === "partial" || recovery.status === "no-feasible-plan").toBe(true);
    if (recovery.status === "ready" || recovery.status === "partial" || recovery.status === "no-feasible-plan") expect(recovery.summary.recoverableOrders).toBe(18);
    expect(impactComparisonSchema.parse(impactFixture).metrics).toHaveLength(5);
  });

  it("supports asynchronous simulation and recovery states", () => {
    expect(simulationSchema.parse({ ...simulationFixture, status: "processing", completedAt: undefined }).status).toBe("processing");
    expect(recoveryPlanSchema.parse({ id: "plan-pending", simulationId: simulationFixture.id, createdAt: simulationFixture.createdAt, status: "queued" }).status).toBe("queued");
  });

  it("supports backend-produced multi geometries", () => {
    const multiLine = { ...disruptionFixture.roads[0], geometry: { type: "MultiLineString" as const, coordinates: [[[106.8, -6.1], [106.9, -6.2]]] } };
    const multiPolygon = { type: "MultiPolygon" as const, coordinates: [[[[106.8, -6.1], [106.9, -6.1], [106.9, -6.2], [106.8, -6.1]]]] };
    expect(disruptionAnalysisSchema.parse({ ...disruptionFixture, roads: [multiLine], historicalFloodGeometry: multiPolygon }).roads[0].geometry.type).toBe("MultiLineString");
  });

  it("rejects formatted or unbounded backend values", () => {
    expect(() => disruptionAnalysisSchema.parse({ ...disruptionFixture, roads: [{ ...disruptionFixture.roads[0], riskProbability: 1.4 }] })).toThrow();
    expect(() => impactComparisonSchema.parse({ ...impactFixture, metrics: impactFixture.metrics.map((metric) => metric.key === "on-time-delivery" ? { ...metric, recovery: 85 } : metric) })).toThrow();
  });
});
