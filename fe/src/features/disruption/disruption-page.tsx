"use client";

import { AlertTriangle, Building2, ChevronLeft, CloudRain, MapPin, Waves, X } from "lucide-react";
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
  return (
    <section aria-label="Status skenario" className="overflow-hidden rounded-[18px] bg-white shadow-[0_0_10px_rgb(0_0_0/25%)]">
      {/* Header — flat top, no curve */}
      <div className="flex h-[56px] items-center justify-center bg-primary-dark">
        <span className="text-[17px] font-bold text-white">Peta Gangguan</span>
      </div>
      <dl className="grid grid-cols-2 gap-4 px-6 py-4 text-[12px]">
        <div>
          <dt className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-[#979797]">
            Kondisi Lingkungan <CloudRain className="size-3.5 text-primary" />
          </dt>
          <dd className="text-[13px] font-semibold text-black">{dynamic ? rainfall?.label : "04 Mar 2025"}</dd>
          <dd className="mt-0.5 text-[11px] leading-tight text-[#5a5a5a]">{dynamic ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta"}</dd>
        </div>
        <div>
          <dt className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-[#979797]">
            Kondisi Operasional <Building2 className="size-3.5 text-primary" />
          </dt>
          <dd className="text-[13px] font-semibold text-black">{operationalConditionLabel(condition)}</dd>
          <dd className="mt-0.5 flex items-center gap-1 text-[11px] text-[#5a5a5a]">
            <MapPin className="size-3 text-primary" /> Jakarta
          </dd>
        </div>
      </dl>
    </section>
  );
}

function ImpactPanel({ data, pending, onPlan, onShowIssues }: { data: DisruptionAnalysis; pending: boolean; onPlan: () => void; onShowIssues: () => void }) {
  const metrics = [
    ["SEGMEN JALAN BERESIKO", data.impact.roadSegmentsAtRisk, true],
    ["PEMASOK TERDAMPAK", data.impact.impactedSupplierIds.length, true],
    ["PESANAN BERESIKO", data.impact.impactedOrderIds.length, true],
    ["PENJUALAN TERDAMPAK", formatCompactIdr(data.impact.salesExposure.amount), false],
  ] as const;

  return (
    <aside className="w-full pb-10 text-black xl:flex xl:h-full xl:w-[295px] xl:flex-col xl:pb-0" aria-label="Dampak operasional">
      {/* Dampak Operasional header */}
      <h2 className="flex h-[80px] items-center justify-center rounded-[42px] bg-[linear-gradient(176deg,#5889c1_-20%,#29405b_87%)] text-[18px] font-semibold text-white shadow-[0_0_10px_rgb(0_0_0/25%)]">
        Dampak Operasional
      </h2>

      {/* Metrics grid */}
      <div className="mt-4 grid shrink-0 grid-cols-2 gap-2.5">
        {metrics.map(([label, value, danger]) => (
          <article
            key={label}
            className="flex h-[115px] min-w-0 flex-col items-center justify-center rounded-[26px] bg-white px-3 text-center shadow-[0_6px_18px_rgb(0_0_0/20%)]"
          >
            <h3 className="min-h-[28px] text-[9px] font-semibold leading-[11px] text-[#4a4a4a]">{label}</h3>
            <div className={`mt-1 max-w-full text-[32px] font-semibold leading-none ${danger ? "text-[#bc0000]" : "text-black"}`}>{value}</div>
            <p className="mt-1.5 text-[9px] font-semibold text-[#979797]">TERESTIMASI</p>
          </article>
        ))}
      </div>

      {/* Lihat Masalah Prioritas button */}
      <button
        type="button"
        onClick={onShowIssues}
        className="mt-4 flex items-center justify-between rounded-[20px] bg-white px-4 py-3.5 shadow-[0_4px_14px_rgb(0_0_0/18%)] transition hover:bg-primary-soft/40"
      >
        <div className="flex items-center gap-2.5">
          <ChevronLeft className="size-5 text-primary-dark" />
          <span className="text-[13px] font-bold text-primary-dark">LIHAT MASALAH PRIORITAS</span>
        </div>
      </button>

      {/* Rencanakan Pemulihan */}
      <button
        type="button"
        onClick={onPlan}
        disabled={pending}
        className="mt-4 h-[80px] w-full shrink-0 rounded-[42px] bg-[linear-gradient(164deg,#eba92d_10%,#856019_141%)] px-5 text-[16px] font-semibold text-white shadow-[0_6px_18px_rgb(0_0_0/24%)] hover:brightness-105 disabled:opacity-60"
      >
        {pending ? "Menyusun Pemulihan..." : "Rencanakan Pemulihan"}
      </button>
    </aside>
  );
}

function IssuesSidebar({ data, open, onClose }: { data: DisruptionAnalysis; open: boolean; onClose: () => void }) {
  return (
    <aside
      className={`flex shrink-0 flex-col bg-white shadow-[-4px_0_20px_rgb(0_0_0/18%)] transition-all duration-300 overflow-hidden ${open ? "w-[300px]" : "w-0"}`}
      aria-label="Masalah prioritas"
      aria-hidden={!open}
    >
      {/* Inner wrapper — keeps content visible at full width while container animates */}
      <div className="flex h-full w-[300px] flex-col">
        {/* Header — flat, no border-radius */}
        <div className="flex h-[56px] shrink-0 items-center justify-between bg-primary-dark px-4">
          <h3 className="text-[14px] font-bold text-white">MASALAH PRIORITAS</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup sidebar masalah prioritas"
            className="grid size-7 place-items-center rounded-full bg-white/15 text-white transition hover:bg-white/30"
          >
            <X className="size-4" />
          </button>
        </div>
        {/* Issues list */}
        <div className="flex-1 overflow-y-auto">
          {data.impact.issues.length === 0 && (
            <p className="p-6 text-center text-[12px] text-[#979797]">Tidak ada masalah prioritas.</p>
          )}
          {data.impact.issues.map((issue) => (
            <article key={issue.id} className="flex min-h-[90px] gap-2.5 border-b border-[#e0e0e0] px-4 py-4 last:border-0">
              <AlertTriangle
                className={`mt-0.5 size-[16px] shrink-0 ${issue.severity === "critical" ? "text-danger" : "text-[#c68000]"}`}
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className={`rounded-[4px] px-1.5 py-0.5 text-[9px] font-semibold uppercase ${severityClass[issue.severity]}`}>
                    {formatRisk(issue.severity)}
                  </span>
                  <strong className="truncate text-[11px] text-black">{issue.subject}</strong>
                </div>
                <p className="mt-1 line-clamp-3 text-[10px] leading-[13px] text-[#5a5a5a]">{issue.description}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </aside>
  );
}

export function DisruptionPage() {
  const params = useSearchParams(), simulationId = params.get("simulation") ?? "", condition = params.get("condition") ?? "normal";
  const query = useDisruptionAnalysis(simulationId), simulation = useSimulation(simulationId), generate = useGenerateRecovery(), router = useRouter();
  const [selected, setSelected] = useState<{ road: RoadRisk; coords: [number, number] } | null>(null);
  const [issuesSidebarOpen, setIssuesSidebarOpen] = useState(false);
  const selectRoad = useCallback((road: RoadRisk, coords: [number, number]) => setSelected({ road, coords }), []);
  const clearSelection = useCallback(() => setSelected(null), []);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        clearSelection();
        setIssuesSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [clearSelection]);
  const facilities = useMemo(() => new Map(query.data?.facilities.map((item) => [item.id, item.name])), [query.data]);
  const createPlan = () =>
    generate.mutate({ id: simulationId }, { onSuccess: () => router.push(`/recovery?simulation=${simulationId}&condition=${encodeURIComponent(condition)}`) });

  const popup = selected ? (
    <div role="dialog" aria-label={`Detail risiko ${selected.road.roadName}`} className="w-[min(320px,90vw)] rounded-lg border border-outline bg-white p-4 shadow-xl">
      <div className="flex justify-between gap-3">
        <div>
          <h2 className="text-[13px] font-semibold">{selected.road.roadName || "Jalan tanpa nama"}</h2>
          <p className="text-[10px] text-muted">
            {selected.road.affectedSupplierIds.map((id) => facilities.get(id) ?? id).join(", ")}
            {" - "}
            {selected.road.affectedWarehouseIds.map((id) => facilities.get(id) ?? id).join(", ")}
          </p>
        </div>
        <button onClick={clearSelection} aria-label="Tutup detail jalan" className="p-1 text-muted">
          <X size={16} />
        </button>
      </div>
      <p className="my-2.5 inline-flex items-center gap-1 rounded border border-danger px-2 py-1 text-[11px] font-semibold text-danger">
        <Waves size={13} /> {formatRisk(selected.road.riskLevel)} risiko rute
      </p>
      <dl className="space-y-1.5 text-[11px]">
        <div className="flex justify-between">
          <dt className="text-muted">Skor risiko</dt>
          <dd className="font-semibold">{selected.road.dynamicRoadRiskScore?.toFixed(2) ?? formatPercent(selected.road.riskProbability)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Perkiraan keterlambatan</dt>
          <dd className="font-semibold text-danger">+{selected.road.estimatedDelayMinutes} mnt</dd>
        </div>
      </dl>
    </div>
  ) : null;

  return (
    <AppShell title="Peta Gangguan">
      {!simulationId && <EmptyState title="Belum ada simulasi yang dipilih" message="Jalankan analisis skenario sebelum membuka analisis gangguan." />}
      {simulationId && query.isLoading && <LoadingState label="Memetakan risiko gangguan banjir..." />}
      {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
      {query.data && (
        <div className="flex min-h-[calc(100vh-80px)] bg-surface-low xl:h-[calc(100vh-80px)] xl:min-h-0 xl:overflow-hidden">
          {/* Map area — shrinks when right sidebar opens */}
          <div className="relative min-h-[620px] flex-1 overflow-hidden">
            <section className="absolute inset-0 overflow-hidden" aria-label="Peta risiko gangguan">
              <DisruptionMap
                data={query.data}
                selectedRoadId={selected?.road.segmentId}
                selectedCoords={selected?.coords}
                onSelectRoad={selectRoad}
                onClearSelection={clearSelection}
                popupContent={popup}
                showChrome={false}
              />
            </section>

            {/* Overlay UI layer */}
            <div className="pointer-events-none relative z-10 flex h-full flex-col gap-5 p-4 xl:block xl:p-0">
              {/* Left card: ScenarioStatus */}
              {simulation.data && (
                <div className="pointer-events-auto w-full max-w-[280px] xl:absolute xl:left-[clamp(24px,3vw,48px)] xl:top-6">
                  <ScenarioStatus simulation={simulation.data} condition={condition} />
                </div>
              )}

              {/* Right panel: ImpactPanel */}
              <div className="pointer-events-auto ml-auto w-full max-w-[295px] xl:absolute xl:bottom-6 xl:right-[clamp(24px,3vw,48px)] xl:top-6">
                <ImpactPanel
                  data={query.data}
                  pending={generate.isPending}
                  onPlan={createPlan}
                  onShowIssues={() => setIssuesSidebarOpen(true)}
                />
                {generate.isError && (
                  <p role="alert" className="mt-2 rounded bg-white p-2 text-[11px] text-danger">
                    {generate.error.message}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Issues Sidebar — in-flow, shifts map to the left */}
          <IssuesSidebar
            data={query.data}
            open={issuesSidebarOpen}
            onClose={() => setIssuesSidebarOpen(false)}
          />
        </div>
      )}
    </AppShell>
  );
}

