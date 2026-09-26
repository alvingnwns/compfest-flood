import type { DemandForecast } from "@/domain/demand-forecast";

export type ForecastRange = "future" | "past" | "both";
const DAY = 86_400_000;

// The first forecast date is the backend's operational Today, not the browser's timezone.
export function selectForecastPoints(forecast: DemandForecast, range: ForecastRange): DemandForecast["points"] {
  const datedForecast = forecast.points.find((point) => point.predicted !== null && /^\d{4}-\d{2}-\d{2}$/.test(point.label));
  if (datedForecast) {
    const today = datedForecast.label;
    const anchor = Date.parse(today + "T00:00:00Z");
    const days = (offset: number) => new Date(anchor + offset * DAY).toISOString().slice(0, 10);
    const merged = new Map<string, DemandForecast["points"][number]>();
    for (const point of forecast.points) {
      const previous = merged.get(point.label);
      merged.set(point.label, { ...point, actual: point.actual ?? previous?.actual ?? null, predicted: point.predicted ?? previous?.predicted ?? null, historySource: point.historySource ?? previous?.historySource });
    }
    const past = [-3, -2, -1].map(days);
    const future = [1, 2, 3].map(days);
    const labels = range === "future" ? [today, ...future] : range === "past" ? [...past, today] : [...past, today, ...future];
    return labels.map((label) => ({ ...(merged.get(label) ?? { actual: null, predicted: null }), label: label === today ? "Hari Ini" : label }));
  }
  const today = forecast.points.findIndex((point) => point.label === "Hari Ini" || point.label === "Today");
  const anchor = today >= 0 ? today : forecast.points.findIndex((point) => point.predicted !== null);
  if (anchor < 0) return forecast.points;
  return range === "future" ? forecast.points.slice(anchor, anchor + 4) : range === "past" ? forecast.points.slice(Math.max(0, anchor - 3), anchor + 1) : forecast.points.slice(Math.max(0, anchor - 3), anchor + 4);
}
