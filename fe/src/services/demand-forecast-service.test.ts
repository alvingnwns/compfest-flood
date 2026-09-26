import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { demandForecastSchema } from "@/domain/demand-forecast";
import { demandForecastService } from "./demand-forecast-service";

describe("demandForecastService", () => {
  it("returns a validated forecast payload", async () => {
    const result = await demandForecastService.getForecast();
    expect(demandForecastSchema.safeParse(result).success).toBe(true);
    expect(result.source).toBe("mock");
    expect(result.horizonDays).toBe(3);
  });
});
