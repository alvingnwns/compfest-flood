"use client";

import { AlertCircle, CheckCircle2, Clock3, CloudRain, Download, Factory, MapPin, Route, ShoppingBag, Truck, Warehouse, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { ImpactMetric } from "@/domain/impact";
import type { Simulation } from "@/domain/scenario";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useImpactComparison, useSimulation } from "@/hooks/use-aruna-data";
import { formatCompactIdr, formatMinutes, formatPercent } from "@/lib/format";
import { exportService } from "@/services/export-service";

const metricIcons = { "orders-fulfilled": Truck, "on-time-delivery": Clock3, "failed-orders": AlertCircle, "average-delay": Clock3, "sales-exposure-risk": ShoppingBag };
const metricLabels: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "Pesanan Terpenuhi", "on-time-delivery": "Pengiriman Tepat Waktu", "failed-orders": "Pesanan Gagal", "average-delay": "Rata-rata Keterlambatan", "sales-exposure-risk": "Risiko Paparan Penjualan" };

function formatMetricValue(metric: ImpactMetric, value: number) {
  if (metric.key === "sales-exposure-risk") return formatCompactIdr(value);
  if (metric.key === "on-time-delivery") return formatPercent(value);
  if (metric.key === "average-delay") return formatMinutes(value);
  if (metric.key === "orders-fulfilled") return `${value}/${metric.total}`;
  return value.toString();
}
function metricDelta(metric: ImpactMetric) {
  if (metric.key === "average-delay") { const delta = metric.recovery - metric.baseline; return { label: `${delta > 0 ? "+" : ""}${delta.toFixed(1).replace(".", ",")} mnt`, better: delta <= 0 }; }
  if (metric.key === "sales-exposure-risk") { const delta = metric.baseline - metric.recovery; return { label: `-${formatCompactIdr(Math.abs(delta))}`, better: delta >= 0 }; }
  if (metric.key === "failed-orders") { const delta = metric.baseline - metric.recovery; return { label: `${delta >= 0 ? "-" : "+"}${Math.abs(delta)} pesanan`, better: delta >= 0 }; }
  if (metric.key === "on-time-delivery") { const delta = Math.round((metric.recovery - metric.baseline) * 100); return { label: `${delta >= 0 ? "+" : ""}${delta} persen`, better: delta >= 0 }; }
  const delta = metric.recovery - metric.baseline;
  return { label: `${delta >= 0 ? "+" : ""}${delta} pesanan`, better: delta >= 0 };
}

function ScenarioStatus({ simulation, condition }: { simulation: Simulation; condition: string }) {
  const dynamic = simulation.analysisMode === "scenario-simulation" && simulation.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.hazard?.rainfallScenario) : undefined;
  return (
    <section aria-label="Status skenario" className="overflow-hidden rounded-[22px] bg-white shadow-[0_0_15px_rgb(0_0_0/18%)]">
      <div className="flex h-[58px] items-center justify-center bg-primary px-5 text-center text-[19px] font-bold text-white">
        Analisis Dampak
      </div>
      <div className="grid grid-cols-2 gap-5 px-7 py-5 text-[12px]">
        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wide text-[#979797]">
            <span>KONDISI LINGKUNGAN</span>
            <CloudRain className="size-[18px] shrink-0 text-primary" />
          </div>
          <div className="text-[14px] font-bold text-black">{dynamic ? rainfall?.label : "04 Mar 2025"}</div>
          <div className="mt-1 text-[12px] leading-tight text-[#5a5a5a]">{dynamic ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta"}</div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wide text-[#979797]">
            <span>KONDISI OPERASIONAL</span>
            <Factory className="size-[18px] shrink-0 text-primary" />
          </div>
          <div className="text-[14px] font-bold text-black">{operationalConditionLabel(condition)}</div>
          <div className="mt-1 flex items-center gap-1.5 text-[12px] text-[#5a5a5a]">
            <MapPin className="size-3.5 shrink-0 text-primary" /> Jakarta
          </div>
        </div>
      </div>
    </section>
  );
}

function MetricCard({ metric }: { metric: ImpactMetric }) {
  const Icon = metricIcons[metric.key], delta = metricDelta(metric), max = Math.max(metric.baseline, metric.recovery, 1);
  const isCurrency = metric.key === "sales-exposure-risk";

  return (
    <article className="flex min-h-[280px] flex-col overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)] print:min-h-0 print:rounded-[18px] print:border print:border-outline/40 print:shadow-none">
      <header className="flex min-h-[82px] items-center justify-between gap-4 bg-primary px-7 py-4 text-white print:min-h-[46px] print:px-4 print:py-2">
        <h3 className="max-w-[82%] text-[17px] font-bold uppercase leading-tight print:text-[13px]">{metricLabels[metric.key]}</h3>
        <Icon className="size-7 shrink-0 print:size-5" strokeWidth={1.7} />
      </header>
      <div className="flex flex-1 flex-col justify-between px-7 py-5 print:p-3.5">
        <div className="grid grid-cols-2 items-center gap-4 print:gap-2">
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-[#5a5a5a] print:text-[11px]">Kondisi Awal</p>
            <span
              className={`mt-2 inline-flex items-center justify-center rounded-[14px] bg-[#d9d9d9] px-3 py-1 font-bold text-[#5a5a5a] print:mt-1 print:px-2.5 print:py-0.5 print:rounded-[8px] ${isCurrency ? "text-[18px] leading-tight print:text-[14px]" : "text-[25px] print:text-[18px]"
                }`}
            >
              {formatMetricValue(metric, metric.baseline)}
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-[16px] font-bold text-[#005a45] print:text-[12px]">ARUNA</p>
            <span
              className={`mt-2 inline-flex items-center justify-center rounded-[16px] bg-[#005a45] px-3.5 py-1 font-bold text-[#00f0b8] print:mt-1 print:px-2.5 print:py-0.5 print:rounded-[8px] ${isCurrency ? "text-[21px] leading-tight print:text-[15px]" : "text-[31px] print:text-[20px]"
                }`}
            >
              {formatMetricValue(metric, metric.recovery)}
            </span>
          </div>
        </div>
        <span
          className={`mt-3 w-max max-w-full rounded-[7px] px-2.5 py-1 text-[11px] font-bold print:mt-2 print:text-[10px] print:py-0.5 ${delta.better ? "bg-success/25 text-[#005a45]" : "bg-amber-100 text-amber-800"
            }`}
        >
          {delta.label}
        </span>
        <div className="mt-4 space-y-2 print:mt-2 print:space-y-1">
          <div className="h-3 overflow-hidden rounded-full bg-[#d9d9d9] print:h-2">
            <div className="h-full rounded-full bg-[#5a5a5a]" style={{ width: `${(metric.baseline / max) * 100}%` }} />
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-[#d9d9d9] print:h-2">
            <div className="h-full rounded-full bg-[#005a45]" style={{ width: `${(metric.recovery / max) * 100}%` }} />
          </div>
        </div>
      </div>
    </article>
  );
}

export function ImpactPage() {
  const params = useSearchParams(), simulationId = params.get("simulation") ?? "", condition = params.get("condition") ?? "normal";
  const query = useImpactComparison(simulationId), simulation = useSimulation(simulationId);
  const [menu, setMenu] = useState(false);

  const dynamic = simulation.data?.analysisMode === "scenario-simulation" && simulation.data?.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.data?.hazard?.rainfallScenario) : undefined;
  const scenarioLabel = dynamic ? `${rainfall?.label ?? "Pola Hujan"} (Simulasi Kondisi)` : "Simulasi Banjir Jakarta (04 Mar 2025)";

  return (
    <AppShell title="Analisis Dampak">
      <div className="impact-pattern min-h-[calc(100vh-80px)] p-4 md:min-h-[calc(100vh-80px)] md:p-6 xl:h-[calc(100vh-80px)] xl:min-h-0 xl:overflow-hidden xl:px-8 xl:py-6 print:min-h-0 print:p-0">
        {/* Executive Print Report Header */}
        <div className="hidden print:block mb-4 border-b-2 border-primary pb-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-[18px] font-bold tracking-wide text-primary-dark">LAPORAN ANALISIS DAMPAK PEMULIHAN</h1>
              <p className="text-[11px] font-medium text-[#5a5a5a]">ARUNA — Sistem Mitigasi &amp; Pemulihan Rantai Pasok</p>
            </div>
            <div className="text-right text-[11px] text-[#5a5a5a] space-y-0.5">
              <div><strong>Skenario:</strong> {scenarioLabel}</div>
              <div><strong>Kondisi:</strong> {operationalConditionLabel(condition)}</div>
              <div><strong>ID Simulasi:</strong> {simulationId || "-"}</div>
            </div>
          </div>
        </div>

        <div className="mx-auto grid max-w-[1480px] items-start gap-7 xl:h-full xl:grid-cols-[325px_minmax(0,1094px)] xl:gap-[36px] print:block print:max-w-none">
          <div className="xl:h-full print:hidden">
            {!simulationId && (
              <EmptyState
                title="Belum ada simulasi yang dipilih"
                message="Selesaikan rencana pemulihan sebelum membandingkan dampak."
              />
            )}
            {simulation.data && <ScenarioStatus simulation={simulation.data} condition={condition} />}
          </div>
          <div className="xl:h-full xl:overflow-y-auto xl:overscroll-contain xl:pb-10 xl:pr-3 print:h-auto print:overflow-visible print:p-0">
            {simulationId && query.isLoading && <LoadingState label="Menghitung perbandingan kondisi awal..." />}
            {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
            {query.data && (
              <>
                <section className="overflow-hidden rounded-[54px] bg-primary/20 shadow-[0_0_8px_rgb(0_0_0/25%)] print:rounded-[20px] print:bg-white print:border print:border-outline/40 print:shadow-none">
                  <header className="flex min-h-[122px] items-center justify-center bg-primary px-8 text-center text-[28px] font-semibold text-white md:text-[32px] print:min-h-[46px] print:py-2.5 print:text-[18px]">
                    DAMPAK PEMULIHAN
                  </header>
                  <div className="p-6 md:p-10 print:p-4">
                    <div className="grid gap-5 lg:grid-cols-12 print:grid-cols-2 print:gap-3">
                      {query.data.metrics.map((metric) => (
                        <div
                          key={metric.key}
                          className={`print-break-avoid ${metric.key === "average-delay"
                              ? "lg:col-span-5 print:col-span-1"
                              : metric.key === "sales-exposure-risk"
                                ? "lg:col-span-7 print:col-span-1"
                                : "lg:col-span-4 print:col-span-1"
                            }`}
                        >
                          <MetricCard metric={metric} />
                        </div>
                      ))}
                    </div>
                    <div className="mt-6 grid gap-5 lg:grid-cols-[.85fr_1.15fr] print:mt-3.5 print:grid-cols-2 print:gap-3 print-break-avoid">
                      <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)] print:rounded-[16px] print:border print:border-outline/40 print:shadow-none">
                        <h2 className="flex min-h-[78px] items-center justify-between bg-primary px-7 text-[17px] font-bold uppercase text-white print:min-h-[42px] print:px-4 print:py-2 print:text-[13px]">
                          Ringkasan Pemulihan <Warehouse className="size-7 print:size-5" />
                        </h2>
                        <div className="space-y-3 p-6 print:p-3.5 print:space-y-2">
                          {[
                            ["Produksi", query.data.actionCounts.manufacturing, Factory],
                            ["Logistik", query.data.actionCounts.logistics, Truck],
                            ["Perdagangan", query.data.actionCounts.commerce, ShoppingBag],
                          ].map(([label, count, Icon]) => {
                            const ItemIcon = Icon as typeof Factory;
                            return (
                              <div
                                key={String(label)}
                                className="flex items-center justify-between border-b border-outline/60 pb-3 last:border-0 print:pb-1.5"
                              >
                                <span className="flex items-center gap-3 text-sm font-semibold print:text-xs">
                                  <ItemIcon className="size-5 text-primary print:size-4" />
                                  {String(label)}
                                </span>
                                <strong className="rounded-lg bg-primary-soft px-3 py-1 text-sm text-primary print:text-xs print:px-2 print:py-0.5">
                                  {String(count)}
                                </strong>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                      <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)] print:rounded-[16px] print:border print:border-outline/40 print:shadow-none">
                        <h2 className="flex min-h-[78px] items-center justify-between bg-primary px-7 text-[17px] font-bold uppercase text-white print:min-h-[42px] print:px-4 print:py-2 print:text-[13px]">
                          Alur Pelaksanaan <Route className="size-7 print:size-5" />
                        </h2>
                        <div className="relative grid grid-cols-4 gap-2 px-5 py-10 before:absolute before:left-[12%] before:right-[12%] before:top-[55px] before:h-1 before:bg-primary print:py-4 print:before:top-[28px]">
                          {[
                            ["Risiko", AlertCircle],
                            ["Evaluasi", Route],
                            ["Pemulihan", Factory],
                            ["Siap", CheckCircle2],
                          ].map(([label, Icon]) => {
                            const StepIcon = Icon as typeof AlertCircle;
                            return (
                              <div
                                key={String(label)}
                                className="relative z-10 flex flex-col items-center gap-3 text-center print:gap-1.5"
                              >
                                <span className="grid size-9 place-items-center rounded-full bg-primary text-white ring-4 ring-white print:size-6">
                                  <StepIcon className="size-4 print:size-3" />
                                </span>
                                <span className="text-[11px] font-semibold text-primary-dark print:text-[9px]">{String(label)}</span>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                    </div>
                    <p className="mt-6 rounded-[18px] bg-white/70 px-5 py-4 text-center text-xs font-medium text-muted print:mt-3 print:py-2 print:text-[10px]">
                      <strong className="text-primary">Pendukung keputusan.</strong> Hasil merupakan estimasi skenario simulasi dan memerlukan tinjauan operator sebelum dilaksanakan.
                    </p>
                  </div>
                </section>
                <div className="no-print print:hidden relative mx-auto mt-8 w-full max-w-[578px]">
                  <button
                    type="button"
                    onClick={() => setMenu((open) => !open)}
                    aria-expanded={menu}
                    className="flex min-h-[96px] w-full items-center justify-center gap-4 rounded-[42px] bg-[linear-gradient(149deg,#eba92d,#856019)] px-8 text-[19px] font-bold text-white shadow-md md:text-[25px]"
                  >
                    <Download className="size-7" /> LIHAT RINGKASAN ANDA
                  </button>
                  {menu && (
                    <div className="absolute bottom-[calc(100%+10px)] left-1/2 z-20 w-[260px] -translate-x-1/2 overflow-hidden rounded-lg border border-outline bg-white py-2 text-sm text-ink shadow-xl">
                      <div className="flex items-center justify-between border-b border-outline px-4 pb-2">
                        <strong>Ekspor Ringkasan</strong>
                        <button
                          type="button"
                          onClick={() => setMenu(false)}
                          aria-label="Tutup menu ekspor"
                          className="p-1 text-muted"
                        >
                          <X className="size-4" />
                        </button>
                      </div>
                      <button
                        className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                        onClick={() => {
                          setMenu(false);
                          exportService.print();
                        }}
                      >
                        Cetak / PDF
                      </button>
                      <button
                        className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                        onClick={() => {
                          setMenu(false);
                          exportService.csv(query.data);
                        }}
                      >
                        Data CSV
                      </button>
                      <button
                        className="block w-full px-4 py-2 text-left hover:bg-surface-low"
                        onClick={() => {
                          setMenu(false);
                          exportService.json(query.data);
                        }}
                      >
                        Ekspor JSON
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
