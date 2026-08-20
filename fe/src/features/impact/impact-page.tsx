"use client";

import { AlertCircle, CheckCircle2, Clock3, Download, Factory, MapPin, Route, ShoppingBag, Truck, Warehouse, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { ImpactMetric } from "@/domain/impact";
import type { Simulation } from "@/domain/scenario";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useImpactComparison, useSimulation } from "@/hooks/use-resilichain-data";
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
  return <section aria-label="Status skenario" className="overflow-hidden rounded-[18px] bg-white shadow-[0_0_10px_rgb(0_0_0/25%)]">
    <div className="flex h-[62px] items-center justify-center bg-primary text-[21px] font-bold text-white">Analisis Dampak</div>
    <dl className="grid min-h-[147px] grid-cols-2 gap-5 px-[32px] py-[18px] text-[12px]">
      <div><dt className="mb-3 text-[10px] font-bold text-[#979797]">KONDISI LINGKUNGAN</dt><dd className="font-semibold text-black">{dynamic ? rainfall?.label : "04 Mar 2025"}</dd><dd className="mt-1 leading-tight text-[#5a5a5a]">{dynamic ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta"}</dd></div>
      <div><dt className="mb-3 text-[10px] font-bold text-[#979797]">KONDISI OPERASIONAL</dt><dd className="font-semibold text-black">{operationalConditionLabel(condition)}</dd><dd className="mt-1 flex items-center gap-1 text-[#5a5a5a]"><MapPin className="size-3 text-primary" /> Jakarta</dd></div>
    </dl>
  </section>;
}

function MetricCard({ metric }: { metric: ImpactMetric }) {
  const Icon = metricIcons[metric.key], delta = metricDelta(metric), max = Math.max(metric.baseline, metric.recovery, 1);
  return <article className="flex min-h-[280px] flex-col overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)]">
    <header className="flex min-h-[82px] items-center justify-between gap-4 bg-primary px-7 py-4 text-white"><h3 className="max-w-[82%] text-[17px] font-bold uppercase leading-tight">{metricLabels[metric.key]}</h3><Icon className="size-7 shrink-0" strokeWidth={1.7} /></header>
    <div className="flex flex-1 flex-col justify-between px-7 py-5">
      <div className="grid grid-cols-2 items-center gap-5">
        <div><p className="text-[12px] font-medium text-[#5a5a5a]">Kondisi Awal</p><span className="mt-2 inline-flex rounded-[14px] bg-[#d9d9d9] px-3 py-1 text-[25px] font-bold text-[#5a5a5a]">{formatMetricValue(metric, metric.baseline)}</span></div>
        <div><p className="text-[13px] font-bold text-[#005a45]">ResiliChain</p><span className="mt-2 inline-flex rounded-[16px] bg-[#005a45] px-3 py-1 text-[31px] font-bold text-[#00f0b8]">{formatMetricValue(metric, metric.recovery)}</span></div>
      </div>
      <span className={`mt-3 w-max max-w-full rounded-[7px] px-2 py-1 text-[11px] font-bold ${delta.better ? "bg-success/25 text-[#005a45]" : "bg-amber-100 text-amber-800"}`}>{delta.label}</span>
      <div className="mt-4 space-y-2"><div className="h-3 overflow-hidden rounded-full bg-[#d9d9d9]"><div className="h-full rounded-full bg-[#5a5a5a]" style={{ width: `${metric.baseline / max * 100}%` }} /></div><div className="h-3 overflow-hidden rounded-full bg-[#d9d9d9]"><div className="h-full rounded-full bg-[#005a45]" style={{ width: `${metric.recovery / max * 100}%` }} /></div></div>
    </div>
  </article>;
}

export function ImpactPage() {
  const params = useSearchParams(), simulationId = params.get("simulation") ?? "", condition = params.get("condition") ?? "normal";
  const query = useImpactComparison(simulationId), simulation = useSimulation(simulationId);
  const [menu, setMenu] = useState(false);

  return <AppShell title="Analisis Dampak"><div className="impact-pattern min-h-[calc(100vh-125px)] px-5 py-10 lg:px-10 xl:h-[calc(100vh-125px)] xl:min-h-0 xl:overflow-hidden">
    <div className="mx-auto grid max-w-[1480px] items-start gap-8 xl:h-full xl:grid-cols-[325px_minmax(0,1094px)] xl:gap-[33px]">
      <div className="xl:h-full">{!simulationId && <EmptyState title="Belum ada simulasi yang dipilih" message="Selesaikan rencana pemulihan sebelum membandingkan dampak." />}{simulation.data && <ScenarioStatus simulation={simulation.data} condition={condition} />}</div>
      <div className="xl:h-full xl:overflow-y-auto xl:overscroll-contain xl:pb-10 xl:pr-3">
        {simulationId && query.isLoading && <LoadingState label="Menghitung perbandingan kondisi awal..." />}
        {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
        {query.data && <>
          <section className="overflow-hidden rounded-[54px] bg-primary/20 shadow-[0_0_8px_rgb(0_0_0/25%)]">
            <header className="flex min-h-[122px] items-center justify-center bg-primary px-8 text-center text-[28px] font-semibold text-white md:text-[32px]">DAMPAK PEMULIHAN</header>
            <div className="p-6 md:p-10">
              <div className="grid gap-5 lg:grid-cols-12">{query.data.metrics.map(metric => <div key={metric.key} className={metric.key === "average-delay" ? "lg:col-span-5" : metric.key === "sales-exposure-risk" ? "lg:col-span-7" : "lg:col-span-4"}><MetricCard metric={metric} /></div>)}</div>
              <div className="mt-6 grid gap-5 lg:grid-cols-[.85fr_1.15fr]">
                <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)]">
                  <h2 className="flex min-h-[78px] items-center justify-between bg-primary px-7 text-[17px] font-bold uppercase text-white">Ringkasan Pemulihan <Warehouse className="size-7" /></h2>
                  <div className="space-y-3 p-6">{[["Produksi", query.data.actionCounts.manufacturing, Factory], ["Logistik", query.data.actionCounts.logistics, Truck], ["Perdagangan", query.data.actionCounts.commerce, ShoppingBag]].map(([label, count, Icon]) => { const ItemIcon = Icon as typeof Factory; return <div key={String(label)} className="flex items-center justify-between border-b border-outline/60 pb-3 last:border-0"><span className="flex items-center gap-3 text-sm font-semibold"><ItemIcon className="size-5 text-primary" />{String(label)}</span><strong className="rounded-lg bg-primary-soft px-3 py-1 text-sm text-primary">{String(count)}</strong></div>; })}</div>
                </section>
                <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_5px_14px_rgb(41_64_91/15%)]">
                  <h2 className="flex min-h-[78px] items-center justify-between bg-primary px-7 text-[17px] font-bold uppercase text-white">Alur Pelaksanaan <Route className="size-7" /></h2>
                  <div className="relative grid grid-cols-4 gap-2 px-5 py-10 before:absolute before:left-[12%] before:right-[12%] before:top-[55px] before:h-1 before:bg-primary">{[["Risiko", AlertCircle], ["Evaluasi", Route], ["Pemulihan", Factory], ["Siap", CheckCircle2]].map(([label, Icon]) => { const StepIcon = Icon as typeof AlertCircle; return <div key={String(label)} className="relative z-10 flex flex-col items-center gap-3 text-center"><span className="grid size-9 place-items-center rounded-full bg-primary text-white ring-4 ring-white"><StepIcon className="size-4" /></span><span className="text-[11px] font-semibold text-primary-dark">{String(label)}</span></div>; })}</div>
                </section>
              </div>
              <p className="mt-6 rounded-[18px] bg-white/70 px-5 py-4 text-center text-xs font-medium text-muted"><strong className="text-primary">Pendukung keputusan.</strong> Hasil merupakan estimasi skenario simulasi dan memerlukan tinjauan operator sebelum dilaksanakan.</p>
            </div>
          </section>
          <div className="relative mx-auto mt-8 w-full max-w-[578px]">
            <button type="button" onClick={() => setMenu(open => !open)} aria-expanded={menu} className="flex min-h-[96px] w-full items-center justify-center gap-4 rounded-[42px] bg-[linear-gradient(149deg,#eba92d,#856019)] px-8 text-[19px] font-bold text-white shadow-md md:text-[25px]"><Download className="size-7" /> LIHAT RINGKASAN ANDA</button>
            {menu && <div className="absolute bottom-[calc(100%+10px)] left-1/2 z-20 w-[260px] -translate-x-1/2 overflow-hidden rounded-lg border border-outline bg-white py-2 text-sm text-ink shadow-xl"><div className="flex items-center justify-between border-b border-outline px-4 pb-2"><strong>Ekspor Ringkasan</strong><button type="button" onClick={() => setMenu(false)} aria-label="Tutup menu ekspor" className="p-1 text-muted"><X className="size-4" /></button></div><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.print()}>Cetak / PDF</button><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.csv(query.data)}>Data CSV</button><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.json(query.data)}>Ekspor JSON</button></div>}
          </div>
        </>}
      </div>
    </div>
  </div></AppShell>;
}
