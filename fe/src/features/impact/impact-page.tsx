"use client";

import { AlertCircle, ArrowDown, ArrowUp, CheckCircle2, Clock3, Download, Factory, Route, ShoppingBag, Truck } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { ImpactMetric } from "@/domain/impact";
import { useImpactComparison } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatMinutes, formatPercent } from "@/lib/format";
import { exportService } from "@/services/export-service";

const metricIcons = {
  "orders-fulfilled": Truck,
  "on-time-delivery": Clock3,
  "failed-orders": AlertCircle,
  "average-delay": Clock3,
  "sales-exposure-risk": ShoppingBag,
};

const metricLabels: Record<ImpactMetric["key"], string> = {
  "orders-fulfilled": "Pesanan Terpenuhi",
  "on-time-delivery": "Pengiriman Tepat Waktu",
  "failed-orders": "Pesanan Gagal",
  "average-delay": "Rata-rata Keterlambatan",
  "sales-exposure-risk": "Risiko Paparan Penjualan",
};

function formatMetricValue(metric: ImpactMetric, num: number): string {
  if (metric.key === "sales-exposure-risk") return formatCompactIdr(num);
  if (metric.key === "on-time-delivery") return formatPercent(num);
  if (metric.key === "average-delay") return formatMinutes(num);
  if (metric.key === "orders-fulfilled") return `${num}/${metric.total}`;
  return num.toString();
}

type MetricEvaluation = {
  label: string;
  isBetter: boolean;
  isNeutral: boolean;
  badgeClass: string;
  IconComponent: typeof ArrowUp;
};

function evaluateMetric(metric: ImpactMetric): MetricEvaluation {
  const delta = metric.recovery - metric.baseline;
  const isZero = Math.abs(delta) < 0.001;

  if (isZero) {
    return {
      label: "Tidak Berubah",
      isBetter: false,
      isNeutral: true,
      badgeClass: "bg-surface-high text-muted",
      IconComponent: ArrowUp,
    };
  }

  if (metric.key === "average-delay") {
    // LOWER IS BETTER: baseline 0.2 -> recovery 1.8 means delay increased by +1.6 mnt (WORSE / TRADE-OFF)
    const delayDelta = metric.recovery - metric.baseline;
    const isWorse = delayDelta > 0;
    const formattedDelta = `${delayDelta > 0 ? "+" : ""}${delayDelta.toFixed(1).replace(".", ",")} mnt`;
    return {
      label: isWorse ? `${formattedDelta} (Trade-off)` : `${formattedDelta} (Lebih Cepat)`,
      isBetter: !isWorse,
      isNeutral: false,
      badgeClass: isWorse
        ? "bg-amber-100 text-amber-800 border border-amber-300"
        : "bg-primary/10 text-primary",
      IconComponent: isWorse ? ArrowUp : ArrowDown,
    };
  }

  if (metric.key === "sales-exposure-risk") {
    // LOWER IS BETTER
    const expDelta = metric.baseline - metric.recovery;
    const isBetter = expDelta > 0;
    const formattedDelta = `${formatCompactIdr(Math.abs(expDelta))} ${isBetter ? "berkurang" : "meningkat"}`;
    return {
      label: formattedDelta,
      isBetter,
      isNeutral: false,
      badgeClass: isBetter ? "bg-primary/10 text-primary" : "bg-danger/10 text-danger",
      IconComponent: isBetter ? ArrowDown : ArrowUp,
    };
  }

  if (metric.key === "failed-orders") {
    // LOWER IS BETTER
    const failedDelta = metric.baseline - metric.recovery;
    const isBetter = failedDelta > 0;
    const formattedDelta = `${failedDelta > 0 ? "-" : "+"}${Math.abs(failedDelta)} pesanan`;
    return {
      label: formattedDelta,
      isBetter,
      isNeutral: false,
      badgeClass: isBetter ? "bg-primary/10 text-primary" : "bg-danger/10 text-danger",
      IconComponent: isBetter ? ArrowDown : ArrowUp,
    };
  }

  if (metric.key === "on-time-delivery") {
    // HIGHER IS BETTER
    const otdDelta = metric.recovery - metric.baseline;
    const isBetter = otdDelta > 0;
    const points = Math.round(otdDelta * 100);
    const formattedDelta = `${points > 0 ? "+" : ""}${points} poin`;
    return {
      label: formattedDelta,
      isBetter,
      isNeutral: false,
      badgeClass: isBetter ? "bg-primary/10 text-primary" : "bg-danger/10 text-danger",
      IconComponent: isBetter ? ArrowUp : ArrowDown,
    };
  }

  // orders-fulfilled (HIGHER IS BETTER)
  const fulfilledDelta = metric.recovery - metric.baseline;
  const isBetter = fulfilledDelta > 0;
  const formattedDelta = `${fulfilledDelta > 0 ? "+" : ""}${fulfilledDelta} pesanan`;
  return {
    label: formattedDelta,
    isBetter,
    isNeutral: false,
    badgeClass: isBetter ? "bg-primary/10 text-primary" : "bg-danger/10 text-danger",
    IconComponent: isBetter ? ArrowUp : ArrowDown,
  };
}

export function ImpactPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("simulation") ?? "";
  const query = useImpactComparison(simulationId);
  const [menu, setMenu] = useState(false);

  // Derive trade-off sentence dynamically if present
  const delayMetric = query.data?.metrics.find((m) => m.key === "average-delay");
  const fulfilledMetric = query.data?.metrics.find((m) => m.key === "orders-fulfilled");
  const tradeOffSentence =
    delayMetric &&
    fulfilledMetric &&
    delayMetric.recovery > delayMetric.baseline &&
    fulfilledMetric.recovery >= fulfilledMetric.baseline
      ? `Rencana pemulihan berhasil mempertahankan/meningkatkan pemenuhan pesanan (${fulfilledMetric.recovery}/${fulfilledMetric.total}), dengan konsekuensi tambahan keterlambatan rata-rata sebesar ${(delayMetric.recovery - delayMetric.baseline).toFixed(1).replace(".", ",")} menit.`
      : null;

  return (
    <AppShell>
      <div className="p-4 md:p-6">
        <div className="mx-auto max-w-[1440px]">
          {!simulationId && (
            <EmptyState
              title="Belum ada simulasi yang dipilih"
              message="Selesaikan rencana pemulihan sebelum membandingkan dampak."
            />
          )}
          {simulationId && query.isLoading && <LoadingState label="Menghitung perbandingan kondisi awal…" />}
          {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
          {query.data && (
            <>
              <div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
                <div>
                  <h1 className="page-title">Dampak Pemulihan</h1>
                  <p className="mt-1 text-sm text-muted">
                    Membandingkan Kondisi Awal (Tanpa Tindakan) dengan Rencana Rekomendasi ResiliChain
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="mono flex gap-4 text-[11px]">
                    <span className="flex items-center gap-2 text-muted">
                      <i className="h-2.5 w-2.5 rounded-sm bg-surface-highest" />
                      Kondisi Awal (Tanpa Tindakan)
                    </span>
                    <span className="flex items-center gap-2 font-semibold text-primary">
                      <i className="h-2.5 w-2.5 rounded-sm bg-primary" />
                      Rencana ResiliChain
                    </span>
                  </div>
                  <div className="relative">
                    <button
                      aria-expanded={menu}
                      onClick={() => setMenu((x) => !x)}
                      className="flex items-center gap-2 rounded-md border border-outline bg-white px-3 py-2 text-sm font-medium hover:bg-surface-low"
                    >
                      <Download size={17} /> Ekspor Ringkasan
                    </button>
                    {menu && (
                      <div className="card absolute right-0 z-20 mt-1 w-40 overflow-hidden py-1 text-sm shadow-lg">
                        <button
                          className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                          onClick={() => exportService.print()}
                        >
                          Cetak / PDF
                        </button>
                        <button
                          className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                          onClick={() => exportService.csv(query.data)}
                        >
                          Data CSV
                        </button>
                        <button
                          className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                          onClick={() => exportService.json(query.data)}
                        >
                          Ekspor JSON
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Trade-off communication banner */}
              {tradeOffSentence && (
                <div className="mb-6 rounded-lg border border-amber-300 bg-amber-50/80 p-3.5 text-xs text-amber-900 shadow-sm">
                  <strong>Ringkasan Analisis Trade-off:</strong> {tradeOffSentence}
                </div>
              )}

              {/* Impact Metrics Grid */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {query.data.metrics.map((metric) => {
                  const Icon = metricIcons[metric.key];
                  const evalResult = evaluateMetric(metric);
                  const ArrowIcon = evalResult.IconComponent;
                  const max = Math.max(metric.baseline, metric.recovery);

                  return (
                    <article
                      key={metric.key}
                      className={`card relative flex min-h-[220px] flex-col justify-between overflow-hidden p-5 ${
                        metric.key === "sales-exposure-risk" ? "md:col-span-2" : ""
                      }`}
                    >
                      <span className="absolute right-2 top-2 rounded bg-surface-low px-2 py-1 text-[9px] font-semibold uppercase text-muted">
                        Estimasi Skenario Simulasi
                      </span>
                      <div>
                        <div className="eyebrow mb-4 flex items-center gap-2">
                          <Icon size={19} />
                          {metricLabels[metric.key]}
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="mono mb-1 text-xs text-muted">Kondisi Awal</div>
                            <div className="text-2xl font-semibold text-muted">
                              {formatMetricValue(metric, metric.baseline)}
                            </div>
                          </div>
                          <div>
                            <div className="mono mb-1 text-xs font-semibold text-primary">Rencana ResiliChain</div>
                            <div className="flex flex-wrap items-end gap-2">
                              <div className="kpi text-primary">{formatMetricValue(metric, metric.recovery)}</div>
                              {!evalResult.isNeutral && (
                                <div
                                  className={`mb-1 flex items-center gap-1 rounded px-2 py-1 text-[10px] font-bold ${evalResult.badgeClass}`}
                                >
                                  <ArrowIcon size={12} />
                                  {evalResult.label}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="mt-5 space-y-2">
                        <div className="h-2 overflow-hidden rounded-full bg-surface-high">
                          <div
                            className="h-full bg-slate-500/50"
                            style={{ width: `${max === 0 ? 0 : (metric.baseline / max) * 100}%` }}
                          />
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-surface-high">
                          <div
                            className="h-full rounded-full bg-primary"
                            style={{ width: `${max === 0 ? 0 : (metric.recovery / max) * 100}%` }}
                          />
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>

              {/* Recovery Action Counts & Execution Workflow */}
              <div className="mt-6 grid gap-4 lg:grid-cols-3">
                <section className="card p-5">
                  <h2 className="section-title mb-4">Ringkasan Tindakan Pemulihan</h2>
                  {[
                    ["Produksi", query.data.actionCounts.manufacturing, Factory],
                    ["Logistik", query.data.actionCounts.logistics, Truck],
                    ["Perdagangan", query.data.actionCounts.commerce, ShoppingBag],
                  ].map(([label, count, Icon]) => {
                    const I = Icon as typeof Factory;
                    return (
                      <div
                        key={String(label)}
                        className="mb-2 flex items-center justify-between rounded-md border border-outline/50 bg-surface-low p-2.5"
                      >
                        <span className="flex items-center gap-3 text-sm font-medium text-ink">
                          <I size={18} className="text-primary" />
                          {String(label)}
                        </span>
                        <span className="mono rounded bg-secondary-soft px-2 py-1 text-[10px] font-bold text-primary">
                          {String(count)} tindakan
                        </span>
                      </div>
                    );
                  })}
                </section>
                <section className="card p-5 lg:col-span-2">
                  <h2 className="section-title mb-8">Alur Pelaksanaan</h2>
                  <div className="relative flex items-start justify-between before:absolute before:left-[8%] before:right-[8%] before:top-4 before:h-0.5 before:bg-primary">
                    {[
                      ["Risiko Terdeteksi", AlertCircle],
                      ["Dampak Dievaluasi", Route],
                      ["Pemulihan Dibuat", Factory],
                      ["Rencana Siap", CheckCircle2],
                    ].map(([label, Icon]) => {
                      const I = Icon as typeof AlertCircle;
                      return (
                        <div key={String(label)} className="relative z-10 flex w-24 flex-col items-center gap-2 text-center">
                          <span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-white ring-4 ring-white">
                            <I size={15} />
                          </span>
                          <span className="mono text-[10px] font-medium text-ink">{String(label)}</span>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </div>
              <div className="mt-4 rounded-lg border border-primary/20 bg-primary-soft/60 p-4 text-sm text-muted">
                <strong className="text-primary">Hanya pendukung keputusan.</strong> Hasil merupakan estimasi skenario simulasi dan memerlukan tinjauan operator sebelum dilaksanakan.
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
