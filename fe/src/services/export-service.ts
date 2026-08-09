import type { ImpactComparison, ImpactMetric } from "@/domain/impact";

const metricLabels: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "Orders Fulfilled", "on-time-delivery": "On-Time Delivery", "failed-orders": "Failed Orders", "average-delay": "Average Delay", "sales-exposure-risk": "Sales Exposure Risk" };
const metricUnits: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "orders", "on-time-delivery": "ratio", "failed-orders": "count", "average-delay": "minutes", "sales-exposure-risk": "IDR" };

function download(content: string, mimeType: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export const exportService = {
  json(data: ImpactComparison) { download(JSON.stringify(data, null, 2), "application/json", `${data.simulationId}-impact.json`); },
  csv(data: ImpactComparison) {
    const rows = [["Metric Key", "Metric", "Baseline", "Recovery", "Unit"], ...data.metrics.map((metric) => [metric.key, metricLabels[metric.key], metric.baseline, metric.recovery, metricUnits[metric.key]])];
    download(rows.map((row) => row.join(",")).join("\n"), "text/csv", `${data.simulationId}-impact.csv`);
  },
  print() { window.print(); },
};
