import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { inventoryOverviewSchema } from "@/domain/inventory";
import { inventoryService } from "./inventory-service";

describe("inventoryService", () => {
  it("returns warehouse data that satisfies the inventory contract", async () => {
    const result = await inventoryService.getOverview();
    expect(inventoryOverviewSchema.safeParse(result).success).toBe(true);
    expect(result.source).toBe("mock");
    expect(result.movements.length).toBeGreaterThan(0);
  });
});
