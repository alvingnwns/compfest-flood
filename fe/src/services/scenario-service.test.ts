import { afterEach, describe, expect, it, vi } from "vitest";
import { publicEnv } from "@/config/public-env";
import { scenarioFixture } from "@/mocks/data";
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
});
