"use client";

import { AlertTriangle, Building2, CloudRain, MapPin, Waves, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { DisruptionAnalysis, RoadRisk } from "@/domain/disruption";
import type { Simulation } from "@/domain/scenario";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useDisruptionAnalysis, useGenerateRecovery, useSimulation } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatPercent, formatRisk } from "@/lib/format";
import { DisruptionMap } from "./disruption-map";

const severityClass = { critical: "bg-danger/10 text-danger", high: "bg-[#c68000]/15 text-[#c68000]", medium: "bg-amber-100 text-amber-700", low: "bg-primary/10 text-primary" };

function ScenarioStatus({ simulation, condition }: { simulation: Simulation; condition: string }) {
  const dynamic = simulation.analysisMode === "scenario-simulation" && simulation.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.hazard?.rainfallScenario) : undefined;
  return <section aria-label="Status skenario" className="overflow-hidden rounded-[18px] bg-white shadow-[0_0_10px_rgb(0_0_0/25%)]">
    <div className="flex h-[62px] items-center justify-center bg-primary text-[22px] font-bold text-white">Peta Gangguan</div>
    <dl className="grid min-h-[147px] grid-cols-2 gap-5 px-[34px] py-[18px] text-[12px]">
      <div><dt className="mb-3 flex items-center gap-2 text-[11px] font-bold text-[#979797]">KONDISI LINGKUNGAN <CloudRain className="size-4 text-primary" /></dt><dd className="font-semibold text-black">{dynamic ? rainfall?.label : "04 Mar 2025"}</dd><dd className="mt-1 leading-tight text-[#5a5a5a]">{dynamic ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta"}</dd></div>
      <div><dt className="mb-3 flex items-center gap-2 text-[11px] font-bold text-[#979797]">KONDISI OPERASIONAL <Building2 className="size-4 text-primary" /></dt><dd className="font-semibold text-black">{operationalConditionLabel(condition)}</dd><dd className="mt-1 flex items-center gap-1 text-[#5a5a5a]"><MapPin className="size-3.5 text-primary" /> Jakarta</dd></div>
    </dl>
  </section>;
}
function ImpactPanel({ data, pending, onPlan }: { data: DisruptionAnalysis; pending: boolean; onPlan: () => void }) {
  const metrics = [["SEGMEN JALAN BERESIKO", data.impact.roadSegmentsAtRisk, true], ["PEMASOK TERDAMPAK", data.impact.impactedSupplierIds.length, true], ["PESANAN BERESIKO", data.impact.impactedOrderIds.length, true], ["PENJUALAN TERDAMPAK", formatCompactIdr(data.impact.salesExposure.amount), false]] as const;
  return <aside className="w-full pb-10 text-black xl:flex xl:h-full xl:w-[319px] xl:flex-col xl:pb-0" aria-label="Dampak operasional">
    <h2 className="flex h-[95px] items-center justify-center rounded-[50px] bg-[linear-gradient(176deg,#5889c1_-20%,#29405b_87%)] text-[21px] font-semibold text-white shadow-[0_0_10px_rgb(0_0_0/25%)]">Dampak Operasional</h2>
    <div className="mt-[19px] grid shrink-0 grid-cols-2 gap-3">{metrics.map(([label, value, danger]) => <article key={label} className="flex h-[132px] min-w-0 flex-col items-center justify-center rounded-[30px] bg-white px-3 text-center shadow-[0_6px_18px_rgb(0_0_0/24%)]"><h3 className="min-h-[30px] text-[10px] font-semibold leading-[12px]">{label}</h3><div className={`mt-1 max-w-full text-[38px] font-semibold leading-none ${danger ? "text-[#bc0000]" : "text-black"}`}>{value}</div><p className="mt-2 text-[10px] font-semibold text-[#979797]">TERESTIMASI</p></article>)}</div>
    <section className="mt-5 overflow-hidden rounded-[30px] bg-white shadow-[0_6px_18px_rgb(0_0_0/24%)] xl:flex xl:min-h-0 xl:flex-1 xl:flex-col">
      <h3 className="flex h-[62px] shrink-0 items-center justify-center border-b border-[#979797] text-[15px] font-semibold">MASALAH PRIORITAS</h3>
      <div className="max-h-[380px] overflow-y-auto xl:max-h-none xl:min-h-0 xl:flex-1">{data.impact.issues.map(issue => <article key={issue.id} className="flex min-h-[95px] gap-2 border-b border-[#979797] px-4 py-4 last:border-0"><AlertTriangle className={`mt-0.5 size-[17px] shrink-0 ${issue.severity === "critical" ? "text-danger" : "text-[#c68000]"}`} /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><span className={`rounded-[4px] px-2 py-0.5 text-[10px] font-semibold uppercase ${severityClass[issue.severity]}`}>{formatRisk(issue.severity)}</span><strong className="truncate text-[11px]">{issue.subject}</strong></div><p className="mt-1 line-clamp-3 text-[10px] leading-[13px] text-[#5a5a5a]">{issue.description}</p></div></article>)}</div>
    </section>
    <button type="button" onClick={onPlan} disabled={pending} className="mt-6 h-[95px] w-full shrink-0 rounded-[50px] bg-[linear-gradient(164deg,#eba92d_10%,#856019_141%)] px-5 text-[19px] font-semibold text-white shadow-[0_6px_18px_rgb(0_0_0/24%)] hover:brightness-105 disabled:opacity-60">{pending ? "Menyusun Pemulihan..." : "Rencanakan Pemulihan"}</button>
  </aside>;
}

export function DisruptionPage() {
  const params = useSearchParams(), simulationId = params.get("simulation") ?? "", condition = params.get("condition") ?? "normal";
  const query = useDisruptionAnalysis(simulationId), simulation = useSimulation(simulationId), generate = useGenerateRecovery(), router = useRouter();
  const [selected, setSelected] = useState<{ road: RoadRisk; coords: [number, number] } | null>(null);
  const selectRoad = useCallback((road: RoadRisk, coords: [number, number]) => setSelected({ road, coords }), []);
  const clearSelection = useCallback(() => setSelected(null), []);
  useEffect(() => { const close = (event: KeyboardEvent) => event.key === "Escape" && clearSelection(); window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [clearSelection]);
  const facilities = useMemo(() => new Map(query.data?.facilities.map(item => [item.id, item.name])), [query.data]);
  const createPlan = () => generate.mutate({ id: simulationId }, { onSuccess: () => router.push(`/recovery?simulation=${simulationId}&condition=${encodeURIComponent(condition)}`) });
  const popup = selected ? <div role="dialog" aria-label={`Detail risiko ${selected.road.roadName}`} className="w-[min(340px,90vw)] rounded-lg border border-outline bg-white p-4 shadow-xl"><div className="flex justify-between gap-3"><div><h2 className="font-semibold">{selected.road.roadName || "Jalan tanpa nama"}</h2><p className="text-[10px] text-muted">{selected.road.affectedSupplierIds.map(id => facilities.get(id) ?? id).join(", ")}{" - "}{selected.road.affectedWarehouseIds.map(id => facilities.get(id) ?? id).join(", ")}</p></div><button onClick={clearSelection} aria-label="Tutup detail jalan" className="p-1 text-muted"><X size={18} /></button></div><p className="my-3 inline-flex items-center gap-1 rounded border border-danger px-2 py-1 text-xs font-semibold text-danger"><Waves size={15} /> {formatRisk(selected.road.riskLevel)} risiko rute</p><dl className="space-y-2 text-xs"><div className="flex justify-between"><dt className="text-muted">Skor risiko</dt><dd className="font-semibold">{selected.road.dynamicRoadRiskScore?.toFixed(2) ?? formatPercent(selected.road.riskProbability)}</dd></div><div className="flex justify-between"><dt className="text-muted">Perkiraan keterlambatan</dt><dd className="font-semibold text-danger">+{selected.road.estimatedDelayMinutes} mnt</dd></div></dl></div> : null;

  return <AppShell title="Peta Gangguan">
    {!simulationId && <EmptyState title="Belum ada simulasi yang dipilih" message="Jalankan analisis skenario sebelum membuka analisis gangguan." />}
    {simulationId && query.isLoading && <LoadingState label="Memetakan risiko gangguan banjir..." />}
    {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
    {query.data && <div className="relative min-h-[calc(100vh-125px)] bg-surface-low xl:h-[calc(100vh-125px)] xl:min-h-0 xl:overflow-hidden">
      <section className="absolute inset-0 min-h-[620px] overflow-hidden" aria-label="Peta risiko gangguan"><DisruptionMap data={query.data} selectedRoadId={selected?.road.segmentId} selectedCoords={selected?.coords} onSelectRoad={selectRoad} onClearSelection={clearSelection} popupContent={popup} showChrome={false} /></section>
      <div className="pointer-events-none relative z-10 flex flex-col gap-6 p-5 xl:block xl:h-full xl:p-0">{simulation.data && <div className="pointer-events-auto w-full max-w-[325px] xl:absolute xl:left-[clamp(40px,4vw,72px)] xl:top-8"><ScenarioStatus simulation={simulation.data} condition={condition} /></div>}<div className="pointer-events-auto ml-auto w-full max-w-[319px] xl:absolute xl:bottom-8 xl:right-[clamp(40px,4vw,72px)] xl:top-8"><ImpactPanel data={query.data} pending={generate.isPending} onPlan={createPlan} />{generate.isError && <p role="alert" className="mt-2 bg-white p-2 text-xs text-danger">{generate.error.message}</p>}</div></div>
    </div>}
  </AppShell>;
}
