import { afterEach, describe, expect, it, vi } from "vitest";
import { publicEnv } from "@/config/public-env";
import { scenarioFixture, simulationFixture } from "@/mocks/data";
import { scenarioService } from "./scenario-service";

describe("scenario service", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests through HTTP and validates the response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(scenarioFixture), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const scenario = await scenarioService.getHistoricalScenario();
    expect(fetchMock).toHaveBeenCalledWith(
      `${publicEnv.NEXT_PUBLIC_API_BASE_URL}/api/scenarios/historical-jakarta`,
      expect.any(Object),
    );
    expect(scenario.companyName).toBe("Nusantara Foods");
  });

  it("rejects malformed backend data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "broken" }), { status: 200 })));
    await expect(scenarioService.getHistoricalScenario()).rejects.toThrow();
  });

  it("maps Q1-Q4 and operational overrides into the exact dynamic request body", async () => {
    for (const rainfallScenario of ["Q1", "Q2", "Q3", "Q4"] as const) {
      const response = { ...simulationFixture, id: `sim-${rainfallScenario}` };
      const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 201, headers: { "Content-Type": "application/json" } }));
      vi.stubGlobal("fetch", fetchMock);
      await scenarioService.runSimulation({
        scenarioId: scenarioFixture.id,
        analysisMode: "scenario-simulation",
        region: "jakarta",
        rainfallScenario,
        vehicleOverrides: [{ id: "V-03", available: false }],
      });
      const request = fetchMock.mock.calls[0][1] as RequestInit;
      expect(JSON.parse(String(request.body))).toEqual({
        scenarioId: scenarioFixture.id,
        analysisMode: "scenario-simulation",
        region: "jakarta",
        rainfallScenario,
        vehicleOverrides: [{ id: "V-03", available: false }],
      });
    }
  });
});
