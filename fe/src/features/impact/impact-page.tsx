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

const metricIcons = { "orders-fulfilled": Truck, "on-time-delivery": Clock3, "failed-orders": AlertCircle, "average-delay": Clock3, "sales-exposure-risk": ShoppingBag };
const metricLabels: Record<ImpactMetric["key"], string> = { "orders-fulfilled": "Orders Fulfilled", "on-time-delivery": "On-Time Delivery", "failed-orders": "Failed Orders", "average-delay": "Average Delay", "sales-exposure-risk": "Sales Exposure Risk" };
function value(metric: ImpactMetric, number: number) {
  if (metric.key === "sales-exposure-risk") return formatCompactIdr(number);
  if (metric.key === "on-time-delivery") return formatPercent(number);
  if (metric.key === "average-delay") return formatMinutes(number);
  if (metric.key === "orders-fulfilled") return `${number}/${metric.total}`;
  return number.toString();
}
function improvement(metric: ImpactMetric) {
  const lower = ["failed-orders", "average-delay", "sales-exposure-risk"].includes(metric.key);
  const delta = lower ? metric.baseline - metric.recovery : metric.recovery - metric.baseline;
  if (metric.key === "on-time-delivery") return `+${Math.round(delta * 100)} pts`;
  if (metric.key === "sales-exposure-risk") return `${formatCompactIdr(delta)} reduction`;
  return metric.baseline === 0 ? "—" : `${Math.round((delta / metric.baseline) * 100)}%`;
}

export function ImpactPage() {
  const simulationId = useSearchParams().get("simulation") ?? ""; const query = useImpactComparison(simulationId); const [menu, setMenu] = useState(false);
  return <AppShell>
    <div className="p-4 md:p-6"><div className="mx-auto max-w-[1440px]">
      {!simulationId && <EmptyState title="No simulation selected" message="Complete a recovery plan before comparing impact." />}
      {simulationId && query.isLoading && <LoadingState label="Calculating baseline comparison…" />}
      {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
      {query.data && <><div className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><h1 className="page-title">Recovery Impact</h1><p className="mt-1 text-sm text-muted">Comparing Baseline Scenario vs. ResiliChain Recommended Plan</p></div><div className="flex flex-wrap items-center gap-4"><div className="mono flex gap-4 text-[11px]"><span className="flex items-center gap-2 text-muted"><i className="h-2.5 w-2.5 rounded-sm bg-surface-highest" />Baseline (Do Nothing)</span><span className="flex items-center gap-2 font-semibold text-primary"><i className="h-2.5 w-2.5 rounded-sm bg-primary" />ResiliChain Plan</span></div><div className="relative"><button aria-expanded={menu} onClick={() => setMenu((x) => !x)} className="flex items-center gap-2 rounded-md border border-outline bg-white px-3 py-2 text-sm font-medium hover:bg-surface-low"><Download size={17} /> Export Summary</button>{menu && <div className="card absolute right-0 z-20 mt-1 w-40 overflow-hidden py-1 text-sm shadow-lg"><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.print()}>Print / PDF</button><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.csv(query.data)}>CSV Data</button><button className="block w-full px-4 py-2 text-left hover:bg-surface-low" onClick={() => exportService.json(query.data)}>JSON Export</button></div>}</div></div></div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{query.data.metrics.map((metric) => { const Icon = metricIcons[metric.key]; const lower = ["failed-orders", "average-delay", "sales-exposure-risk"].includes(metric.key); const max = Math.max(metric.baseline, metric.recovery); return <article key={metric.key} className={`card relative flex min-h-[220px] flex-col justify-between overflow-hidden p-5 ${metric.key === "sales-exposure-risk" ? "md:col-span-2" : ""}`}><span className="absolute right-2 top-2 rounded bg-surface-low px-2 py-1 text-[9px] font-semibold uppercase text-muted">Simulated Scenario Estimate</span><div><div className="eyebrow mb-4 flex items-center gap-2"><Icon size={19} />{metricLabels[metric.key]}</div><div className="grid grid-cols-2 gap-4"><div><div className="mono mb-1 text-xs text-muted">Baseline</div><div className="text-2xl font-semibold text-muted">{value(metric, metric.baseline)}</div></div><div><div className="mono mb-1 text-xs font-semibold text-primary">ResiliChain Plan</div><div className="flex flex-wrap items-end gap-2"><div className="kpi text-primary">{value(metric, metric.recovery)}</div><div className="mb-1 flex items-center gap-1 rounded bg-secondary-soft px-2 py-1 text-[10px] font-bold text-primary">{lower ? <ArrowDown size={12} /> : <ArrowUp size={12} />}{improvement(metric)}</div></div></div></div></div><div className="mt-5 space-y-2"><div className="h-2 overflow-hidden rounded-full bg-surface-high"><div className="h-full bg-slate-500/50" style={{ width: `${max === 0 ? 0 : (metric.baseline / max) * 100}%` }} /></div><div className="h-2 overflow-hidden rounded-full bg-surface-high"><div className="h-full rounded-full bg-primary" style={{ width: `${max === 0 ? 0 : (metric.recovery / max) * 100}%` }} /></div></div></article>; })}</div>
        <div className="mt-6 grid gap-4 lg:grid-cols-3"><section className="card p-5"><h2 className="section-title mb-4">Recovery Actions Summary</h2>{[["Manufacturing", query.data.actionCounts.manufacturing, Factory], ["Logistics", query.data.actionCounts.logistics, Truck], ["Commerce", query.data.actionCounts.commerce, ShoppingBag]].map(([label, count, Icon]) => { const I = Icon as typeof Factory; return <div key={String(label)} className="mb-2 flex items-center justify-between rounded-md border border-outline/50 bg-surface-low p-2"><span className="flex items-center gap-3 text-sm font-medium"><I size={18} />{String(label)}</span><span className="mono rounded bg-secondary-soft px-2 py-1 text-[10px] font-bold">{String(count)} actions</span></div>; })}</section><section className="card p-5 lg:col-span-2"><h2 className="section-title mb-8">Execution Pipeline</h2><div className="relative flex items-start justify-between before:absolute before:left-[8%] before:right-[8%] before:top-4 before:h-0.5 before:bg-primary">{[["Risk Detected", AlertCircle], ["Impact Evaluated", Route], ["Recovery Generated", Factory], ["Plan Ready", CheckCircle2]].map(([label, Icon]) => { const I = Icon as typeof AlertCircle; return <div key={String(label)} className="relative z-10 flex w-24 flex-col items-center gap-2 text-center"><span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-white ring-4 ring-white"><I size={15} /></span><span className="mono text-[10px] font-medium">{String(label)}</span></div>; })}</div></section></div>
        <div className="mt-4 rounded-lg border border-primary/20 bg-primary-soft/60 p-4 text-sm text-muted"><strong className="text-primary">Decision support only.</strong> Results are simulated scenario estimates and require operator review before execution.</div></>}
    </div></div>
  </AppShell>;
}
