import type { ImpactComparison, ImpactMetric } from "@/domain/impact";
import { formatImpactMetricValue, impactMetricDelta } from "@/features/impact/impact-presentation";

const metricLabels: Record<ImpactMetric["key"], string> = {
  "orders-fulfilled": "Pesanan Terpenuhi",
  "on-time-delivery": "Pengiriman Tepat Waktu",
  "failed-orders": "Pesanan Gagal",
  "average-delay": "Rata-rata Keterlambatan",
  "sales-exposure-risk": "Risiko Paparan Penjualan",
};

const metricUnits: Record<ImpactMetric["key"], string> = {
  "orders-fulfilled": "pesanan",
  "on-time-delivery": "rasio",
  "failed-orders": "jumlah",
  "average-delay": "menit",
  "sales-exposure-risk": "IDR",
};

export type ImpactExportContext = {
  scenario: {
    id: string;
    label: string;
    analysisMode: string;
    operationalCondition: string;
    rainfallScenario?: string;
  };
};

function observationCount(metric: ImpactMetric, phase: "baseline" | "recovery"): number | undefined {
  if (metric.key !== "average-delay") return undefined;
  return phase === "baseline" ? metric.baselineObservationCount : metric.recoveryObservationCount;
}

function available(metric: ImpactMetric, phase: "baseline" | "recovery"): boolean {
  const count = observationCount(metric, phase);
  return count === undefined || count > 0;
}

function rawDelta(metric: ImpactMetric): number | null {
  if (!available(metric, "baseline") || !available(metric, "recovery")) return null;
  return Number((metric.recovery - metric.baseline).toFixed(12));
}

export function impactExportPayload(data: ImpactComparison, context: ImpactExportContext) {
  return {
    simulationId: data.simulationId,
    scenario: context.scenario,
    businessDataSource: data.businessDataSource,
    recoveryStatus: data.recoveryStatus,
    metrics: data.metrics.map((metric) => {
      const delta = impactMetricDelta(metric);
      return {
        id: metric.key,
        label: metricLabels[metric.key],
        unit: metricUnits[metric.key],
        baseline: {
          raw: metric.baseline,
          display: formatImpactMetricValue(metric, "baseline"),
          available: available(metric, "baseline"),
          observationCount: observationCount(metric, "baseline"),
        },
        recovery: {
          raw: metric.recovery,
          display: formatImpactMetricValue(metric, "recovery"),
          available: available(metric, "recovery"),
          observationCount: observationCount(metric, "recovery"),
        },
        delta: {
          raw: rawDelta(metric),
          display: delta.label,
          trend: delta.trend,
        },
      };
    }),
    actionCounts: data.actionCounts,
  };
}

function csvCell(value: string | number | null | undefined): string {
  if (value == null) return "";
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function impactCsv(data: ImpactComparison, context: ImpactExportContext): string {
  const payload = impactExportPayload(data, context);
  const rows: Array<Array<string | number | null | undefined>> = [
    ["ID Simulasi", payload.simulationId],
    ["ID Skenario", payload.scenario.id],
    ["Skenario", payload.scenario.label],
    ["Mode Analisis", payload.scenario.analysisMode],
    ["Kondisi Operasional", payload.scenario.operationalCondition],
    ["Pola Hujan", payload.scenario.rainfallScenario],
    ["Sumber Data Bisnis", payload.businessDataSource],
    ["Status Pemulihan", payload.recoveryStatus],
    [],
    [
      "Kunci Metrik",
      "Metrik",
      "Kondisi Awal",
      "Hasil Optimizer",
      "Delta",
      "Trend",
      "Nilai Awal Mentah",
      "Nilai Pemulihan Mentah",
      "Delta Mentah",
      "Observasi Awal",
      "Observasi Pemulihan",
      "Satuan",
    ],
    ...payload.metrics.map((metric) => [
      metric.id,
      metric.label,
      metric.baseline.display,
      metric.recovery.display,
      metric.delta.display,
      metric.delta.trend,
      metric.baseline.raw,
      metric.recovery.raw,
      metric.delta.raw,
      metric.baseline.observationCount,
      metric.recovery.observationCount,
      metric.unit,
    ]),
  ];
  return rows.map((row) => row.map(csvCell).join(",")).join("\n");
}

function download(content: string, mimeType: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export const exportService = {
  json(data: ImpactComparison, context: ImpactExportContext) {
    download(
      JSON.stringify(impactExportPayload(data, context), null, 2),
      "application/json",
      `${data.simulationId}-impact.json`,
    );
  },
  csv(data: ImpactComparison, context: ImpactExportContext) {
    download(impactCsv(data, context), "text/csv", `${data.simulationId}-impact.csv`);
  },
  print() {
    window.print();
  },
};
