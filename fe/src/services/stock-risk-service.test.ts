import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { stockRiskService } from "./stock-risk-service";

describe("stockRiskService", () => {
  it("returns validated stock-risk analysis", async () => {
    const result = await stockRiskService.getOverview();

    expect(result.source).toBe("mock");
    expect(result.materials).toHaveLength(5);
    expect(result.materials[0]).toMatchObject({ name: "Mangga", difference: -4 });
  });
});
