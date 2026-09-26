import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { optimizationPlanService } from "./optimization-plan-service";

describe("optimizationPlanService", () => {
  it("returns validated optimization recommendations", async () => {
    const result = await optimizationPlanService.getPlan();
    expect(result.source).toBe("mock");
    expect(result.actions).toHaveLength(3);
    expect(result.actions[0]).toMatchObject({ materialName: "Mangga", priority: "high" });
  });
});
