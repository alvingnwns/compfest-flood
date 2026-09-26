import { beforeEach, describe, expect, it, vi } from "vitest";
import { demandForecastSchema } from "@/domain/demand-forecast";
import { demandForecastService } from "./demand-forecast-service";
const api = vi.hoisted(() => ({ getProducts: vi.fn(), getForecast: vi.fn() }));
vi.mock("@/lib/inventory-api", () => ({ usesInventoryApi: () => true }));
vi.mock("./inventory-api-data", () => api);

beforeEach(() => vi.resetAllMocks());
describe("Empty forecast service boundary", () => {
  it("returns a typed empty catalogue without requesting or inventing a forecast", async () => {
    api.getProducts.mockResolvedValue([]);
    const data = await demandForecastService.getForecast();
    expect(demandForecastSchema.safeParse(data).success).toBe(true);
    expect(data).toMatchObject({ source: "api", productId: "", products: [], points: [], details: [] });
    expect(api.getForecast).not.toHaveBeenCalled();
  });
  it("does not mask API failures with empty or mock data", async () => {
    api.getProducts.mockRejectedValue(new Error("API unavailable"));
    await expect(demandForecastService.getForecast()).rejects.toThrow("API unavailable");
    expect(api.getForecast).not.toHaveBeenCalled();
  });
  it("rejects a missing product identity when the catalogue is not empty", () => {
    expect(demandForecastSchema.safeParse({ source: "api", productId: "", productName: "", horizonDays: 3, totalPredictedSales: 0, products: [{ id: "one", name: "Juice" }], points: [], details: [] }).success).toBe(false);
  });
});
