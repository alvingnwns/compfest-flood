import { describe, expect, it } from "vitest";
import { HAZARD_SCENARIOS, OPERATIONAL_PRESETS, RAINFALL_SCENARIOS, getOperationalPreset } from "@/features/scenario/scenario-presets";
import { runSimulationRequestSchema } from "@/domain/scenario";
import { publicEnv } from "@/config/public-env";

describe("scenario configuration & operational presets", () => {
  it("provides 1 historical hazard scenario and 4 operational presets", () => {
    expect(HAZARD_SCENARIOS).toHaveLength(1);
    expect(HAZARD_SCENARIOS[0].id).toBe("scenario-jakarta-20250304");
    expect(HAZARD_SCENARIOS[0].badge).toBe("HISTORIS");

    expect(OPERATIONAL_PRESETS).toHaveLength(4);
    const ids = OPERATIONAL_PRESETS.map((p) => p.id);
    expect(ids).toEqual(["normal", "limited-vehicle", "critical-stock", "severe-disruption"]);
  });

  it("getOperationalPreset returns default preset if requested ID is unknown", () => {
    expect(getOperationalPreset("unknown-id").id).toBe("normal");
  });

  it("validates runSimulationRequest payload with operational overrides", () => {
    const validPayload = {
      scenarioId: "scenario-jakarta-20250304",
      vehicleOverrides: [{ id: "V-03", available: false, capacityUnits: 200 }],
      inventoryOverrides: [{ facilityId: "wh-east", productId: "prod-a", quantity: 150 }],
    };
    const parsed = runSimulationRequestSchema.parse(validPayload);
    expect(parsed.scenarioId).toBe("scenario-jakarta-20250304");
    expect(parsed.vehicleOverrides?.[0]?.available).toBe(false);
    expect(parsed.inventoryOverrides?.[0]?.quantity).toBe(150);
    expect(parsed.analysisMode).toBe("historical-replay");
  });

  it("requires region and rainfall pattern only for scenario simulation", () => {
    expect(runSimulationRequestSchema.safeParse({ scenarioId: "scenario-jakarta-20250304", analysisMode: "scenario-simulation" }).success).toBe(false);
    expect(runSimulationRequestSchema.safeParse({ scenarioId: "scenario-jakarta-20250304", analysisMode: "scenario-simulation", region: "jakarta", rainfallScenario: "Q3" }).success).toBe(true);
    expect(runSimulationRequestSchema.safeParse({ scenarioId: "scenario-jakarta-20250304" }).success).toBe(true);
  });

  it("maps exactly four internal rainfall IDs to conservative display labels", () => {
    expect(RAINFALL_SCENARIOS.map((item) => item.id)).toEqual(["Q1", "Q2", "Q3", "Q4"]);
    expect(RAINFALL_SCENARIOS.every((item) => item.label.startsWith("Pola Hujan"))).toBe(true);
    expect(RAINFALL_SCENARIOS.map((item) => item.label).join(" ").toLowerCase()).not.toContain("probabilitas");
  });

  it("ensures publicEnv defaults to api mode and not mock", () => {
    expect(publicEnv.NEXT_PUBLIC_DATA_SOURCE).toBe("api");
  });
});
