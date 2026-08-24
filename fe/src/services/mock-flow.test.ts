import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { setupServer } from "msw/node";
import { businessImportResponseSchema } from "@/domain/business-data";
import { apiErrorSchema } from "@/domain/common";
import { disruptionAnalysisSchema } from "@/domain/disruption";
import { impactComparisonSchema } from "@/domain/impact";
import { recoveryPlanSchema } from "@/domain/recovery";
import { scenarioSchema, simulationSchema } from "@/domain/scenario";
import { handlers } from "@/mocks/handlers";

const server = setupServer(...handlers);
const api = "http://localhost/api";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("primary mocked API flow", () => {
  it("completes Scenario -> Simulation -> Disruption -> Recovery -> Impact", async () => {
    const scenario = scenarioSchema.parse(await (await fetch(`${api}/scenarios/historical-jakarta`)).json());

    const simulationResponse = await fetch(`${api}/simulations`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenarioId: scenario.id }),
    });
    expect(simulationResponse.status).toBe(201);
    const simulation = simulationSchema.parse(await simulationResponse.json());

    expect(simulationSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}`)).json()).status).toBe("completed");
    expect(disruptionAnalysisSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}/disruption`)).json()).simulationId).toBe(simulation.id);

    const generationResponse = await fetch(`${api}/simulations/${simulation.id}/recovery`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
    });
    expect(generationResponse.status).toBe(201);
    expect(recoveryPlanSchema.parse(await generationResponse.json()).simulationId).toBe(simulation.id);
    expect(recoveryPlanSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}/recovery`)).json()).status).toBe("partial");
    expect(impactComparisonSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}/impact`)).json()).metrics).toHaveLength(5);
  });

  it("returns the frozen structured error envelope", async () => {
    const response = await fetch(`${api}/simulations`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ scenarioId: "missing" }),
    });
    expect(response.status).toBe(404);
    expect(apiErrorSchema.parse(await response.json()).code).toBe("scenario_not_found");
  });

  it("keeps MSW dynamic responses aligned with backend schemas", async () => {
    const response = await fetch(`${api}/simulations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenarioId: "scenario-jakarta-20250304", analysisMode: "scenario-simulation", region: "jakarta", rainfallScenario: "Q3" }),
    });
    const simulation = simulationSchema.parse(await response.json());
    expect(simulation.analysisMode).toBe("scenario-simulation");
    expect(simulation.hazard?.rainfallScenario).toBe("Q3");
    const disruption = disruptionAnalysisSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}/disruption`)).json());
    expect(disruption.roads.every((road) => road.dynamicRoadRiskScore !== undefined)).toBe(true);
  });

  it("completes custom upload preview -> simulation -> impact provenance flow", async () => {
    const template = await fetch(`${api}/business-data/template`);
    expect(template.status).toBe(200);
    const form = new FormData();
    form.append("file", new File([await template.blob()], "business.xlsx"));
    const imported = businessImportResponseSchema.parse(await (await fetch(`${api}/business-data/import`, {
      method: "POST",
      body: form,
    })).json());
    expect(imported.summary.totalOrderValue).toBe(9_280_000);

    const simulation = simulationSchema.parse(await (await fetch(`${api}/simulations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenarioId: "scenario-jakarta-20250304",
        businessSnapshotId: imported.businessSnapshotId,
      }),
    })).json());
    expect(simulation.businessDataSource).toBe("custom");
    expect(simulation.businessSnapshotId).toBe(imported.businessSnapshotId);
    expect(disruptionAnalysisSchema.parse(await (await fetch(`${api}/simulations/${simulation.id}/disruption`)).json()).simulationId).toBe(simulation.id);
  });
});
