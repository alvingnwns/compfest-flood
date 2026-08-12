"use client";

import { AlertTriangle, ArrowRight, Factory, Route, ShieldAlert, ShoppingBag, Truck, Warehouse, Waves, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { ModelProvenanceCard } from "@/components/simulation/model-provenance-card";
import type { RoadRisk } from "@/domain/disruption";
import { useDisruptionAnalysis, useGenerateRecovery, useSimulation } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatPercent, formatRisk } from "@/lib/format";
import { DisruptionMap } from "./disruption-map";

const severityClass = { critical: "text-danger bg-danger/10", high: "text-warning bg-orange-100", medium: "text-amber-700 bg-amber-100", low: "text-primary bg-primary/10" };

export function DisruptionPage() {
  const simulationId = useSearchParams().get("simulation") ?? ""; const query = useDisruptionAnalysis(simulationId); const simulation = useSimulation(simulationId); const generate = useGenerateRecovery(); const router = useRouter();
  const [selected, setSelected] = useState<RoadRisk | null>(null);
  const handleSelect = useCallback((road: RoadRisk) => setSelected(road), []);
  const clearSelection = useCallback(() => setSelected(null), []);
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") clearSelection(); };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [clearSelection]);
  const facilities = useMemo(() => new Map(query.data?.facilities.map((item) => [item.id, item.name])), [query.data]);
  const recoveryRoute = query.data?.routes.find((route) => route.type === "recovery");
  const baselineRoute = query.data?.routes.find((route) =>
    route.type === "baseline" &&
    (!recoveryRoute ||
      (route.originFacilityId === recoveryRoute.originFacilityId &&
        route.destinationFacilityId === recoveryRoute.destinationFacilityId)));
  const exposureReduction = baselineRoute && recoveryRoute && baselineRoute.floodExposureProbability > 0 ? Math.round((1 - recoveryRoute.floodExposureProbability / baselineRoute.floodExposureProbability) * 100) : null;
  const createPlan = () => generate.mutate(simulationId, { onSuccess: () => router.push(`/recovery?simulation=${simulationId}`) });

  return <AppShell>
    {!simulationId && <EmptyState title="Belum ada simulasi yang dipilih" message="Jalankan skenario historis sebelum membuka analisis gangguan." />}
    {simulationId && query.isLoading && <LoadingState label="Memetakan risiko gangguan banjir…" />}
    {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
    {query.data && <div className="flex h-[calc(100vh-64px)] min-h-[680px] flex-col xl:flex-row">
      <section className="relative min-h-[520px] flex-1 overflow-hidden bg-surface-low">
        <DisruptionMap data={query.data} selectedRoadId={selected?.segmentId} onSelectRoad={handleSelect} onClearSelection={clearSelection} />
        <h1 className="absolute left-4 top-4 rounded-lg border border-outline bg-white/95 px-4 py-2 text-xl font-semibold shadow-sm backdrop-blur">Analisis Gangguan Banjir</h1>
        <div className="absolute bottom-5 left-5 space-y-2">{baselineRoute && <div className="card w-max px-4 py-2 text-[10px] font-semibold uppercase"><span className="mr-3 inline-block w-8 border-t-2 border-dashed border-danger align-middle" />Rute normal · {baselineRoute.etaMinutes} mnt · {formatRisk(baselineRoute.floodExposure)} paparan</div>}{recoveryRoute && <div className="card w-max px-4 py-2 text-[10px] font-semibold uppercase text-primary"><span className="mr-3 inline-block h-0.5 w-8 bg-primary align-middle" />Rute ResiliChain · {recoveryRoute.etaMinutes} mnt · {formatRisk(recoveryRoute.floodExposure)} paparan{baselineRoute && <div className="mono ml-11 mt-1 normal-case text-muted">{recoveryRoute.etaMinutes - baselineRoute.etaMinutes >= 0 ? "+" : ""}{recoveryRoute.etaMinutes - baselineRoute.etaMinutes} menit waktu tempuh{exposureReduction !== null && <> · <strong className="text-primary">-{exposureReduction}% proyeksi paparan</strong></>}</div>}</div>}<p className="mono text-[10px] text-muted">Estimasi risiko — bukan jaminan banjir akan terjadi.</p></div>
        {selected && <div role="dialog" aria-label={`Detail risiko ${selected.roadName}`} className="card absolute left-1/2 top-1/3 w-[min(340px,90%)] -translate-x-1/2 p-4 shadow-lg"><div className="mb-1 flex items-start justify-between gap-3"><h2 className="font-semibold">{selected.roadName}</h2><button type="button" onClick={clearSelection} aria-label="Tutup detail jalan" className="rounded p-1 text-muted transition hover:bg-surface-high hover:text-ink"><X size={18} /></button></div><p className="mono mb-3 text-[11px] text-muted">{selected.affectedSupplierIds.map((id) => facilities.get(id)).join(", ")} → {selected.affectedWarehouseIds.map((id) => facilities.get(id)).join(", ")}</p><div className={`mb-3 inline-flex items-center gap-1 rounded border px-2 py-1 text-xs font-semibold ${selected.riskLevel === "critical" || selected.riskLevel === "high" ? "border-danger bg-danger/5 text-danger" : selected.riskLevel === "medium" ? "border-warning bg-orange-50 text-warning" : "border-primary bg-primary/5 text-primary"}`}><Waves size={15} /> {formatPercent(selected.riskProbability)} {formatRisk(selected.riskLevel)} risiko gangguan</div><dl className="space-y-2 text-xs"><div className="flex justify-between border-b border-outline/40 pb-1"><dt className="text-muted">Perkiraan keterlambatan tambahan</dt><dd className={`mono font-semibold ${selected.estimatedDelayMinutes > 0 ? "text-danger" : "text-primary"}`}>+{selected.estimatedDelayMinutes} mnt</dd></div><div className="flex justify-between gap-4 border-b border-outline/40 pb-1"><dt className="text-muted">Faktor risiko</dt><dd className="text-right font-medium">{selected.riskFactors.map((x) => x.label).join(", ")}</dd></div><div className="flex justify-between"><dt className="text-muted">Pesanan terdampak</dt><dd className="mono text-right font-medium">{selected.affectedOrderIds.join(", ")}</dd></div></dl><p className="mono mt-3 text-[10px] italic text-muted">Estimasi skenario · hanya pendukung keputusan</p></div>}
      </section>
      <aside className="w-full shrink-0 overflow-y-auto border-l border-outline bg-surface p-6 xl:w-[400px]"><div className="mb-5 flex items-center justify-between border-b border-outline pb-4"><h2 className="text-lg font-semibold">Dampak Operasional</h2><ShieldAlert className="text-muted" size={20} /></div>{simulation.data?.modelProvenance && <ModelProvenanceCard provenance={simulation.data.modelProvenance} version={simulation.data.modelVersion} />}<div className="grid grid-cols-2 gap-x-4 gap-y-6 border-b border-outline pb-6">{[["Segmen Jalan Berisiko", query.data.impact.roadSegmentsAtRisk, Route, true], ["Pemasok Terdampak", query.data.impact.impactedSupplierIds.length, Factory, true], ["Pesanan Berisiko", query.data.impact.impactedOrderIds.length, ShoppingBag, false], ["Perkiraan Paparan Penjualan", formatCompactIdr(query.data.impact.salesExposure.amount), Truck, false]].map(([label, value, Icon, danger]) => { const I = Icon as typeof Route; return <div key={String(label)}><div className="eyebrow mb-1 flex items-center gap-1"><I size={13} />{String(label)}</div><div className={`text-[28px] font-semibold leading-none ${danger ? "text-danger" : "text-ink"}`}>{String(value)}</div><div className="mono mt-1 text-[10px] text-muted">Estimasi simulasi</div></div>; })}</div>
        <div className="py-6"><h3 className="eyebrow mb-3">Masalah Prioritas</h3>{query.data.impact.issues.map((issue) => <button key={issue.id} className="flex w-full gap-3 border-b border-outline/50 px-2 py-3 text-left transition hover:bg-surface-low"><AlertTriangle size={19} className={issue.severity === "critical" ? "text-danger" : "text-warning"} /><span className="flex-1"><span className="mb-1 flex items-center justify-between gap-2"><span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${severityClass[issue.severity]}`}>{formatRisk(issue.severity)}</span><span className="mono text-[10px] text-muted">{issue.subject}</span></span><span className="block text-[13px] leading-snug text-muted">{issue.description}</span></span></button>)}</div>
        <button onClick={createPlan} disabled={generate.isPending} className="mt-auto flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"><Warehouse size={18} />{generate.isPending ? "Menyusun rencana terkoordinasi…" : "Buat Rencana Pemulihan"}<ArrowRight size={17} /></button>{generate.isError && <p role="alert" className="mt-2 text-xs text-danger">{generate.error.message}</p>}
      </aside>
    </div>}
  </AppShell>;
}
