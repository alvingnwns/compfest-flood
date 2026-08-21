import type { ImpactComparison, ImpactMetric } from "@/domain/impact";
import { formatCompactIdr, formatMinutes, formatPercent } from "@/lib/format";

export type MetricTrend = "improved" | "worsened" | "unchanged" | "unavailable";
export type MetricPhase = "baseline" | "recovery";

const higherIsBetter = new Set<ImpactMetric["key"]>(["orders-fulfilled", "on-time-delivery"]);

export const noDelayObservationMessage = "Tidak ada pesanan terkirim untuk menghitung rata-rata keterlambatan.";

type RecoveryStatus = ImpactComparison["recoveryStatus"];

const statusCopy: Record<RecoveryStatus, {
  reportTitle: string;
  headline: string;
  recoveryLabel: string;
  summaryTitle: string;
  steps: string[];
  noticeTitle?: string;
  noticeBody?: string;
  footer: string;
}> = {
  ready: {
    reportTitle: "LAPORAN ANALISIS DAMPAK PEMULIHAN",
    headline: "DAMPAK PEMULIHAN",
    recoveryLabel: "ARUNA",
    summaryTitle: "Ringkasan Pemulihan",
    steps: ["Risiko", "Evaluasi", "Pemulihan", "Siap"],
    footer: "Hasil merupakan estimasi skenario simulasi dan memerlukan tinjauan operator sebelum dilaksanakan.",
  },
  partial: {
    reportTitle: "LAPORAN DAMPAK RENCANA PARSIAL",
    headline: "DAMPAK RENCANA PARSIAL",
    recoveryLabel: "Rencana Parsial",
    summaryTitle: "Ringkasan Rencana Parsial",
    steps: ["Risiko", "Evaluasi", "Rencana Parsial", "Tinjau"],
    noticeTitle: "Rencana Pemulihan Parsial",
    noticeBody: "Sebagian kebutuhan belum dapat dipenuhi. Rencana ini memerlukan tinjauan operator sebelum dipertimbangkan untuk pelaksanaan.",
    footer: "Hasil merupakan estimasi skenario simulasi dan memerlukan tinjauan operator sebelum dilaksanakan.",
  },
  "no-feasible-plan": {
    reportTitle: "LAPORAN HASIL TANPA RENCANA LAYAK",
    headline: "HASIL TANPA RENCANA LAYAK",
    recoveryLabel: "Hasil Tanpa Rencana",
    summaryTitle: "Ringkasan Hasil Optimizer",
    steps: ["Risiko", "Evaluasi", "Tidak Layak"],
    noticeTitle: "Tidak Ada Rencana Pemulihan yang Layak",
    noticeBody: "Nilai hasil menggambarkan keluaran analitis ketika optimizer tidak menemukan rencana yang dapat dijalankan, bukan keberhasilan pemulihan.",
    footer: "Optimizer tidak menghasilkan rencana yang dapat dilaksanakan. Tinjau kendala dan kapasitas sebelum menjalankan ulang simulasi.",
  },
};

export function impactStatusPresentation(status: RecoveryStatus) {
  return statusCopy[status];
}

function hasDelayObservation(metric: ImpactMetric, phase: MetricPhase): boolean {
  if (metric.key !== "average-delay") return true;
  return phase === "baseline" ? metric.baselineObservationCount > 0 : metric.recoveryObservationCount > 0;
}

export function formatImpactMetricValue(metric: ImpactMetric, phase: MetricPhase): string {
  if (!hasDelayObservation(metric, phase)) return "N/A";
  const value = metric[phase];
  if (metric.key === "sales-exposure-risk") return formatCompactIdr(value);
  if (metric.key === "on-time-delivery") return formatPercent(value);
  if (metric.key === "average-delay") return formatMinutes(value);
  if (metric.key === "orders-fulfilled") return `${value}/${metric.total}`;
  return value.toString();
}

export function impactMetricDelta(metric: ImpactMetric): { label: string; trend: MetricTrend } {
  if (!hasDelayObservation(metric, "baseline") || !hasDelayObservation(metric, "recovery")) {
    return { label: "Tidak tersedia", trend: "unavailable" };
  }

  const delta = metric.recovery - metric.baseline;
  if (delta === 0) return { label: "Tidak berubah", trend: "unchanged" };

  const trend: MetricTrend = (higherIsBetter.has(metric.key) ? delta > 0 : delta < 0) ? "improved" : "worsened";
  const direction = delta > 0 ? "Naik" : "Turun";
  const absolute = Math.abs(delta);

  if (metric.key === "sales-exposure-risk") {
    return { label: `${direction} ${formatCompactIdr(absolute)}`, trend };
  }
  if (metric.key === "on-time-delivery") {
    return { label: `${direction} ${Math.round(absolute * 100)} poin persentase`, trend };
  }
  if (metric.key === "average-delay") {
    return { label: `${direction} ${absolute.toFixed(1).replace(".", ",")} mnt`, trend };
  }
  return { label: `${direction} ${absolute} pesanan`, trend };
}
