"use client";

import type { Map as MapLibreMap } from "maplibre-gl";
import { AlertTriangle, ChevronLeft, ChevronRight, CloudRain, Factory, MapPin, Minus, Plus, Waves, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { EmptyState, ErrorState, FullPageState, LoadingState } from "@/components/ui/states";
import type { DisruptionAnalysis, RoadRisk } from "@/domain/disruption";
import type { Simulation } from "@/domain/scenario";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useDisruptionAnalysis, useGenerateRecovery, useSimulation } from "@/hooks/use-aruna-data";
import { formatCompactIdr, formatPercent, formatRisk } from "@/lib/format";
import { DisruptionMap } from "./disruption-map";
import { RecoveryLoadingOverlay } from "./recovery-loading-overlay";

const severityClass = { critical: "bg-danger/10 text-danger", high: "bg-[#c68000]/15 text-[#c68000]", medium: "bg-amber-100 text-amber-700", low: "bg-primary/10 text-primary" };

function ScenarioStatus({ simulation, condition }: { simulation: Simulation; condition: string }) {
  const dynamic = simulation.analysisMode === "scenario-simulation" && simulation.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.hazard?.rainfallScenario) : undefined;
  return (
    <section aria-label="Status skenario" className="overflow-hidden rounded-[22px] bg-white shadow-[0_0_15px_rgb(0_0_0/18%)]">
      <div className="flex h-[58px] items-center justify-center bg-primary px-5 text-center text-[19px] font-bold text-white">
        Peta Gangguan
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

export function ImpactPanel({
  data,
  pending,
  issuesOpen,
  selectedIssueId,
  onPlan,
  onToggleIssues,
}: {
  data: DisruptionAnalysis;
  pending: boolean;
  issuesOpen: boolean;
  selectedIssueId?: string | null;
  onPlan: () => void;
  onToggleIssues: () => void;
}) {
  const metrics = [
    { label: "SEGMEN RISIKO TINGGI/KRITIS", value: data.impact.roadSegmentsAtRisk, danger: true, isCurrency: false },
    { label: "PEMASOK DENGAN RUTE BERISIKO", value: data.impact.impactedSupplierIds.length, danger: true, isCurrency: false },
    {
      label: "PESANAN TERPAPAR RISIKO",
      value: data.impact.impactedOrderIds.length,
      danger: true,
      isCurrency: false,
      help: "Pesanan dengan rute atau dependensi pasok yang memiliki paparan tinggi/kritis. Tidak berarti pesanan pasti gagal.",
    },
    {
      label: "NILAI PESANAN BERISIKO",
      value: formatCompactIdr(data.impact.salesExposure.amount),
      danger: false,
      isCurrency: true,
      help: "Total nilai pesanan yang terkait langsung dengan rute atau pasokan berisiko tinggi/kritis. Bukan nilai kerugian aktual.",
    },
  ] as const;

  return (
    <aside className="w-full pb-10 text-black xl:flex xl:h-full xl:w-[295px] xl:flex-col xl:pb-0" aria-label="Dampak operasional">
      {/* Dampak Operasional header */}
      <h2 className="flex h-[80px] items-center justify-center rounded-[42px] bg-[linear-gradient(176deg,#5889c1_-20%,#29405b_87%)] text-[18px] font-semibold text-white shadow-[0_0_10px_rgb(0_0_0/25%)]">
        Dampak Operasional
      </h2>
      <p className="mt-2 px-2 text-center text-[10px] leading-[13px] text-[#5a5a5a]">
        Paparan risiko sebelum pemulihan berdasarkan rute baseline dan nilai pesanan terkait.
      </p>

      {/* Metrics grid */}
      <div className="mt-3 grid shrink-0 grid-cols-2 gap-2.5">
        {metrics.map(({ label, value, danger, isCurrency, ...metric }) => (
          <article
            key={label}
            title={"help" in metric ? metric.help : undefined}
            className="flex h-[126px] min-w-0 flex-col items-center justify-between rounded-[24px] bg-white px-3 py-3 text-center shadow-[0_6px_18px_rgb(0_0_0/20%)]"
          >
            <h3 className="flex min-h-[28px] items-center justify-center text-[10px] font-bold leading-[13px] text-[#4a4a4a]">
              {label}
            </h3>
            <div
              className={`flex items-center justify-center font-bold ${
                isCurrency ? "text-[20px] leading-tight" : "text-[32px] leading-none"
              } ${danger ? "text-[#bc0000]" : "text-black"}`}
            >
              {value}
            </div>
            <p className="text-[10px] font-semibold tracking-wider text-[#979797]">TERESTIMASI</p>
          </article>
        ))}
      </div>

      {/* Lihat Masalah Prioritas button — acts as toggle */}
      <button
        type="button"
        onClick={onToggleIssues}
        aria-expanded={issuesOpen}
        className="mt-4 flex w-full items-center justify-between rounded-[20px] bg-white px-4 py-3.5 shadow-[0_4px_14px_rgb(0_0_0/18%)] transition hover:bg-primary-soft/40 active:scale-[.99]"
      >
        <div className="flex items-center gap-2.5">
          {issuesOpen ? (
            <ChevronRight className="size-5 shrink-0 text-primary-dark" />
          ) : (
            <ChevronLeft className="size-5 shrink-0 text-primary-dark" />
          )}
          <span className="text-[13px] font-bold text-primary-dark">LIHAT MASALAH PRIORITAS</span>
        </div>
        {selectedIssueId && (
          <span className="rounded-full bg-primary px-2 py-0.5 text-[9px] font-bold text-white">
            1 Aktif
          </span>
        )}
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

export function IssuesSidebar({
  data,
  open,
  selectedIssueId,
  onSelectIssue,
  onClose,
}: {
  data: DisruptionAnalysis;
  open: boolean;
  selectedIssueId: string | null;
  onSelectIssue: (issueId: string | null) => void;
  onClose: () => void;
}) {
  return (
    <aside
      className={`flex shrink-0 flex-col overflow-hidden bg-white shadow-[-4px_0_20px_rgb(0_0_0/18%)] transition-all duration-300 ${
        open ? "w-[320px]" : "w-0"
      }`}
      aria-label="Masalah prioritas"
      aria-hidden={!open}
    >
      {/* Inner wrapper — keeps content visible at full width while container animates */}
      <div className="flex h-full w-[320px] flex-col">
        {/* Header — flat, no border-radius */}
        <div className="flex min-h-[72px] shrink-0 items-center justify-between gap-3 bg-primary-dark px-4 py-3">
          <div>
            <h3 className="text-[14px] font-bold text-white">MASALAH PRIORITAS</h3>
            <p className="mt-0.5 text-[10px] leading-tight text-white/75">
              Pilih masalah untuk menyorot rute di peta.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup sidebar masalah prioritas"
            className="grid size-7 place-items-center rounded-full bg-white/15 text-white transition hover:bg-white/30"
          >
            <X className="size-4" />
          </button>
        </div>

        {/* Focus indicator / reset header */}
        {selectedIssueId && (
          <div className="flex items-center justify-between border-b border-primary/20 bg-primary/10 px-4 py-2 text-[11px] font-medium text-primary-dark">
            <span>Fokus rute aktif di peta</span>
            <button
              type="button"
              onClick={() => onSelectIssue(null)}
              className="font-bold underline hover:text-black"
              aria-label="Hapus fokus rute"
            >
              Tampilkan semua
            </button>
          </div>
        )}

        {/* Issues list */}
        <div className="flex-1 overflow-y-auto">
          {data.impact.issues.length === 0 && (
            <p className="p-6 text-center text-[12px] text-[#979797]">Tidak ada masalah prioritas.</p>
          )}
          {data.impact.issues.map((issue) => {
            const isSelected = selectedIssueId === issue.id;
            return (
              <button
                key={issue.id}
                type="button"
                onClick={() => onSelectIssue(isSelected ? null : issue.id)}
                aria-pressed={isSelected}
                aria-label={`Fokuskan masalah: ${issue.subject}`}
                className={`group flex min-h-[112px] w-full cursor-pointer gap-2.5 border-b border-[#e0e0e0] px-4 py-4 text-left transition last:border-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary ${
                  isSelected
                    ? "bg-primary/10 ring-2 ring-inset ring-primary/40"
                    : "hover:bg-black/[0.02]"
                }`}
              >
                <AlertTriangle
                  className={`mt-0.5 size-[16px] shrink-0 ${
                    issue.severity === "critical" ? "text-danger" : "text-[#c68000]"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span
                      className={`rounded-[4px] px-1.5 py-0.5 text-[9px] font-semibold uppercase ${
                        severityClass[issue.severity]
                      }`}
                    >
                      {formatRisk(issue.severity)}
                    </span>
                    <strong className="truncate text-[11px] text-black">{issue.subject}</strong>
                  </div>
                  <p className="mt-1 line-clamp-3 text-[10px] leading-[13px] text-[#5a5a5a]">
                    {issue.description}
                  </p>
                  <span
                    className={`mt-2 inline-flex items-center gap-1 text-[10px] font-bold transition ${
                      isSelected ? "text-primary-dark" : "text-primary group-hover:translate-x-0.5"
                    }`}
                  >
                    <MapPin className="size-3" />
                    {isSelected ? "Sedang disorot" : "Sorot di peta"}
                    {!isSelected && <ChevronRight className="size-3" />}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
}

export function DisruptionPage() {
  const params = useSearchParams(),
    simulationId = params.get("simulation") ?? "",
    condition = params.get("condition") ?? "normal";
  const query = useDisruptionAnalysis(simulationId),
    simulation = useSimulation(simulationId),
    generate = useGenerateRecovery(),
    router = useRouter();
  const [selected, setSelected] = useState<{ road: RoadRisk; coords: [number, number] } | null>(null);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [issuesSidebarOpen, setIssuesSidebarOpen] = useState(false);
  const mapRef = useRef<MapLibreMap | null>(null);
  const selectRoad = useCallback((road: RoadRisk, coords: [number, number]) => setSelected({ road, coords }), []);
  const clearSelection = useCallback(() => setSelected(null), []);
  const selectIssue = useCallback((issueId: string | null) => {
    setSelectedIssueId(issueId);
    if (issueId) {
      setSelected(null);
      setIssuesSidebarOpen(false);
    }
  }, []);

  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        clearSelection();
        setSelectedIssueId(null);
        setIssuesSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [clearSelection]);

  const facilities = useMemo(
    () => new Map(query.data?.facilities.map((item) => [item.id, item.name])),
    [query.data]
  );
  const selectedIssue = useMemo(
    () => query.data?.impact.issues.find((issue) => issue.id === selectedIssueId),
    [query.data, selectedIssueId],
  );
  const createPlan = () =>
    generate.mutate(
      { id: simulationId },
      {
        onSuccess: () =>
          router.push(`/recovery?simulation=${simulationId}&condition=${encodeURIComponent(condition)}`),
      }
    );

  const popup = selected ? (
    <div
      role="dialog"
      aria-label={`Detail risiko ${selected.road.roadName}`}
      className="w-[min(320px,90vw)] rounded-lg border border-outline bg-white p-4 shadow-xl"
    >
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
          <dd className="font-semibold">
            {selected.road.dynamicRoadRiskScore?.toFixed(2) ??
              formatPercent(selected.road.riskProbability)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Perkiraan keterlambatan</dt>
          <dd className="font-semibold text-danger">+{selected.road.estimatedDelayMinutes} mnt</dd>
        </div>
      </dl>
    </div>
  ) : null;

  if (!simulationId) {
    return (
      <AppShell title="Peta Gangguan">
        <FullPageState>
          <EmptyState
            title="Belum ada simulasi yang dipilih"
            message="Jalankan analisis skenario sebelum membuka analisis gangguan."
          />
        </FullPageState>
      </AppShell>
    );
  }

  return (
    <AppShell title="Peta Gangguan">
      {query.isLoading && <LoadingState label="Memetakan risiko gangguan banjir..." />}
      {query.isError && (
        <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />
      )}
      {query.data && (
        <div className="relative flex min-h-[calc(100vh-80px)] bg-surface-low xl:h-[calc(100vh-80px)] xl:min-h-0 xl:overflow-hidden">
          {/* Map area — shrinks when right sidebar opens */}
          <div className="relative min-h-[620px] flex-1 overflow-hidden">
            <section className="absolute inset-0 overflow-hidden" aria-label="Peta risiko gangguan">
              <DisruptionMap
                data={query.data}
                selectedRoadId={selected?.road.segmentId}
                selectedCoords={selected?.coords}
                selectedIssueId={selectedIssueId}
                onSelectRoad={selectRoad}
                onClearSelection={clearSelection}
                popupContent={popup}
                showChrome={false}
                onMapReady={(map) => {
                  mapRef.current = map;
                }}
              />
            </section>

            {/* Overlay UI layer */}
            <div className="pointer-events-none relative z-10 flex h-full flex-col gap-5 p-4 xl:block xl:p-0">
              {/* Left card: ScenarioStatus + Zoom Controls */}
              {simulation.data && (
                <div className="pointer-events-auto w-full max-w-[325px] xl:absolute xl:left-8 xl:top-6">
                  <ScenarioStatus simulation={simulation.data} condition={condition} />

                  {/* Map Zoom Controls — cleanly situated under condition card near sidebar */}
                  <div className="mt-3 flex items-center gap-1.5 rounded-[16px] border border-outline/30 bg-white p-1.5 shadow-[0_4px_14px_rgb(0_0_0/16%)] w-fit">
                    <button
                      type="button"
                      onClick={() => mapRef.current?.zoomIn()}
                      aria-label="Perbesar peta"
                      title="Perbesar peta"
                      className="grid size-9 place-items-center rounded-[12px] bg-surface-low text-primary font-bold transition hover:bg-primary hover:text-white active:scale-95"
                    >
                      <Plus className="size-5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => mapRef.current?.zoomOut()}
                      aria-label="Perkecil peta"
                      title="Perkecil peta"
                      className="grid size-9 place-items-center rounded-[12px] bg-surface-low text-primary font-bold transition hover:bg-primary hover:text-white active:scale-95"
                    >
                      <Minus className="size-5" />
                    </button>
                  </div>
                </div>
              )}

              {/* Right panel: ImpactPanel */}
              <div className="pointer-events-auto ml-auto w-full max-w-[295px] xl:absolute xl:bottom-6 xl:right-8 xl:top-6">
                <ImpactPanel
                  data={query.data}
                  pending={generate.isPending}
                  issuesOpen={issuesSidebarOpen}
                  selectedIssueId={selectedIssueId}
                  onPlan={createPlan}
                  onToggleIssues={() => setIssuesSidebarOpen((v) => !v)}
                />
                {generate.isError && (
                  <p role="alert" className="mt-2 rounded bg-white p-2 text-[11px] text-danger">
                    {generate.error.message}
                  </p>
                )}
              </div>

              {selectedIssue && (
                <div
                  role="status"
                  className="pointer-events-auto mx-auto flex max-w-[min(440px,calc(100vw-2rem))] items-center gap-3 rounded-2xl border border-primary/20 bg-white px-4 py-3 shadow-[0_6px_20px_rgb(0_0_0/20%)] xl:absolute xl:bottom-6 xl:left-1/2 xl:-translate-x-1/2"
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
                    <MapPin className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[9px] font-bold uppercase tracking-wide text-primary">Rute disorot di peta</p>
                    <p className="truncate text-[11px] font-semibold text-black">{selectedIssue.subject}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => selectIssue(null)}
                    className="shrink-0 rounded-lg px-2 py-1 text-[10px] font-bold text-primary-dark transition hover:bg-primary/10"
                  >
                    Hapus sorotan
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Issues Sidebar — in-flow, shifts map to the left */}
          <IssuesSidebar
            data={query.data}
            open={issuesSidebarOpen}
            selectedIssueId={selectedIssueId}
            onSelectIssue={selectIssue}
            onClose={() => setIssuesSidebarOpen(false)}
          />

          {generate.isPending && <RecoveryLoadingOverlay />}
        </div>
      )}
    </AppShell>
  );
}

