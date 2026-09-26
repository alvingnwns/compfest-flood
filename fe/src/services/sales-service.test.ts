import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { salesOverviewSchema } from "@/domain/sales";
import { salesService } from "./sales-service";

describe("salesService", () => {
  it("returns sales data that satisfies the inventory sales contract", async () => {
    const result = await salesService.getOverview();
    expect(salesOverviewSchema.safeParse(result).success).toBe(true);
    expect(result.source).toBe("mock");
    expect(result.transactions).toHaveLength(5);
  });
});
