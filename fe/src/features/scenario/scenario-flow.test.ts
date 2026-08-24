import { describe, expect, it } from "vitest";
import {
  showsEnvironmentalCondition,
  showsOperationalFlow,
  showsWeatherSimulation,
} from "./scenario-flow";

describe("scenario business-data flow", () => {
  it("waits for a source selection before showing the operational flow", () => {
    expect(showsOperationalFlow(undefined)).toBe(false);
    expect(showsOperationalFlow("demo")).toBe(true);
    expect(showsOperationalFlow("custom")).toBe(true);
  });

  it("shows environmental choices only for demo data", () => {
    expect(showsEnvironmentalCondition("demo")).toBe(true);
    expect(showsEnvironmentalCondition("custom")).toBe(false);
  });

  it("keeps weather simulation visible for both selected data sources", () => {
    expect(showsWeatherSimulation(undefined)).toBe(false);
    expect(showsWeatherSimulation("demo")).toBe(true);
    expect(showsWeatherSimulation("custom")).toBe(true);
  });
});
