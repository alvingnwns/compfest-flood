import { describe, expect, it } from "vitest";
import { demandForecastMock } from "@/mocks/demand-forecast-data";
import { selectForecastPoints } from "./forecast-range";

describe("Forecast date ranges", () => {
  const forecast = {
    ...demandForecastMock,
    points: [
      { label: "2026-09-23", actual: 0, predicted: null, historySource: "OBSERVED_SALES" },
      { label: "2026-09-25", actual: 10, predicted: null, historySource: "OBSERVED_SALES" },
      { label: "2026-09-26", actual: 4, predicted: null, historySource: "OBSERVED_SALES" },
      { label: "2026-09-26", actual: null, predicted: 12 },
      { label: "2026-09-27", actual: null, predicted: 15 },
      { label: "2026-09-28", actual: null, predicted: 18 },
    ],
  };
  it("starts the forward range at operational Today without inventing a fourth prediction", () => {
    const points = selectForecastPoints(forecast, "future");
    expect(points.map((point) => point.label)).toEqual(["Hari Ini", "2026-09-27", "2026-09-28"]);
    expect(points[0]).toMatchObject({ actual: 4, predicted: 12, historySource: "OBSERVED_SALES" });
  });
  it("ends the backward range at Today, preserving zero and missing history distinctly", () => {
    const points = selectForecastPoints(forecast, "past");
    expect(points.map((point) => point.label)).toEqual(["2026-09-23", "2026-09-24", "2026-09-25", "Hari Ini"]);
    expect(points[0].actual).toBe(0);
    expect(points[1]).toMatchObject({ actual: null, predicted: null });
  });
  it("combines history and predictions chronologically with one Today point", () => {
    const points = selectForecastPoints(forecast, "both");
    expect(points).toHaveLength(6);
    expect(points.filter((point) => point.label === "Hari Ini")).toHaveLength(1);
  });
});
