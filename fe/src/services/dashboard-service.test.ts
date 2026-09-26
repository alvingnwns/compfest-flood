import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { dashboardSummarySchema } from "@/domain/dashboard";
import { dashboardService } from "./dashboard-service";

describe("dashboardService", () => {
  it("returns a dashboard payload that satisfies the inventory contract", async () => {
    const result = await dashboardService.getSummary();
    expect(dashboardSummarySchema.safeParse(result).success).toBe(true);
    expect(result.source).toBe("mock");
    expect(result.metrics).toHaveLength(4);
  });
});
