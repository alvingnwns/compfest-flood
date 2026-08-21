import type { ImpactComparison, ImpactMetric } from "@/domain/impact";

const metricLabels: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "Pesanan Terpenuhi", "on-time-delivery": "Pengiriman Tepat Waktu", "failed-orders": "Pesanan Gagal", "average-delay": "Rata-rata Keterlambatan", "sales-exposure-risk": "Risiko Paparan Penjualan" };
const metricUnits: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "pesanan", "on-time-delivery": "rasio", "failed-orders": "jumlah", "average-delay": "menit", "sales-exposure-risk": "IDR" };

function download(content: string, mimeType: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export function impactCsv(data: ImpactComparison): string {
  const rows: Array<Array<string | number>> = [
    ["ID Simulasi", data.simulationId],
    ["Sumber Data Bisnis", data.businessDataSource],
    ["Status Pemulihan", data.recoveryStatus],
    [],
    ["Kunci Metrik", "Metrik", "Kondisi Awal", "Hasil Optimizer", "Satuan"],
    ...data.metrics.map((metric) => [
      metric.key,
      metricLabels[metric.key],
      metric.baseline,
      metric.recovery,
      metricUnits[metric.key],
    ]),
  ];
  return rows.map((row) => row.join(",")).join("\n");
}

export const exportService = {
  json(data: ImpactComparison) { download(JSON.stringify(data, null, 2), "application/json", `${data.simulationId}-impact.json`); },
  csv(data: ImpactComparison) {
    download(impactCsv(data), "text/csv", `${data.simulationId}-impact.csv`);
  },
  print() { window.print(); },
};
