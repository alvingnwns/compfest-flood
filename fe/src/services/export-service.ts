import type { ImpactComparison, ImpactMetric } from "@/domain/impact";

const metricLabels: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "Pesanan Terpenuhi", "on-time-delivery": "Pengiriman Tepat Waktu", "failed-orders": "Pesanan Gagal", "average-delay": "Rata-rata Keterlambatan", "sales-exposure-risk": "Risiko Paparan Penjualan" };
const metricUnits: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "pesanan", "on-time-delivery": "rasio", "failed-orders": "jumlah", "average-delay": "menit", "sales-exposure-risk": "IDR" };

function download(content: string, mimeType: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export const exportService = {
  json(data: ImpactComparison) { download(JSON.stringify(data, null, 2), "application/json", `${data.simulationId}-impact.json`); },
  csv(data: ImpactComparison) {
    const rows = [["Kunci Metrik", "Metrik", "Kondisi Awal", "Pemulihan", "Satuan"], ...data.metrics.map((metric) => [metric.key, metricLabels[metric.key], metric.baseline, metric.recovery, metricUnits[metric.key]])];
    download(rows.map((row) => row.join(",")).join("\n"), "text/csv", `${data.simulationId}-impact.csv`);
  },
  print() { window.print(); },
};
