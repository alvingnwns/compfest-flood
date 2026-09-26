import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { describe, expect, it } from "vitest";
import { posSimulatorService } from "./pos-simulator-service";

describe("posSimulatorService", () => {
  it("returns an insufficient-stock result for the initial order", async () => {
    const catalogue = await posSimulatorService.getCatalogue();
    const result = await posSimulatorService.checkout({ items: catalogue.initialOrder });
    expect(result.status).toBe("insufficient-stock");
  });

  it("completes an order within available stock", async () => {
    const result = await posSimulatorService.checkout({ items: [{ productId: "orange", quantity: 1 }] });
    expect(result).toEqual({ status: "success", transactionId: "TRS-00125" });
  });
});
