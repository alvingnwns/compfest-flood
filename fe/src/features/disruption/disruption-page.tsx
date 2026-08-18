"use client";

import { AlertTriangle, ArrowRight, Factory, Route, ShieldAlert, ShoppingBag, Truck, Warehouse, Waves, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ScenarioContextCard } from "@/components/simulation/scenario-context-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { ModelProvenanceCard } from "@/components/simulation/model-provenance-card";
import type { RoadRisk } from "@/domain/disruption";
import { useDisruptionAnalysis, useGenerateRecovery, useSimulation } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatPercent, formatRisk } from "@/lib/format";
import { DisruptionMap } from "./disruption-map";
import { CANDIDATE_ROUTE_COLOR, riskAwareCandidateLabel } from "./route-semantics";

const severityClass = {
  critical: "text-danger bg-danger/10",
  high: "text-warning bg-orange-100",
  medium: "text-amber-700 bg-amber-100",
  low: "text-primary bg-primary/10",
};

export function DisruptionPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("simulation") ?? "";
  const operationalCondition = searchParams.get("condition") ?? "normal";
  const query = useDisruptionAnalysis(simulationId);
  const simulation = useSimulation(simulationId);
  const generate = useGenerateRecovery();
  const router = useRouter();

  const [selectedState, setSelectedState] = useState<{ road: RoadRisk; coords: [number, number] } | null>(null);
  const handleSelect = useCallback((road: RoadRisk, coords: [number, number]) => {
    setSelectedState({ road, coords });
  }, []);
  const clearSelection = useCallback(() => setSelectedState(null), []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") clearSelection();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [clearSelection]);

  const facilities = useMemo(() => new Map(query.data?.facilities.map((item) => [item.id, item.name])), [query.data]);

  const candidateRoute = query.data?.routes.find((route) => route.type === "recovery");
  const baselineRoute = query.data?.routes.find(
    (route) =>
      route.type === "baseline" &&
      (!candidateRoute ||
        (route.originFacilityId === candidateRoute.originFacilityId &&
          route.destinationFacilityId === candidateRoute.destinationFacilityId))
  );
  const exposureReduction =
    baselineRoute && candidateRoute && baselineRoute.floodExposureProbability > 0
      ? Math.round((1 - candidateRoute.floodExposureProbability / baselineRoute.floodExposureProbability) * 100)
      : null;

  const createPlan = () =>
    generate.mutate(
      { id: simulationId },
      { onSuccess: () => router.push(`/recovery?simulation=${simulationId}&condition=${encodeURIComponent(operationalCondition)}`) }
    );

  const popupNode = selectedState ? (
    <div
      role="dialog"
      aria-label={`Detail risiko ${selectedState.road.roadName || "Jalan tanpa nama"}`}
      className="card w-[min(340px,90vw)] p-4 shadow-xl"
    >
      <div className="mb-1 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-ink">{selectedState.road.roadName || "Jalan tanpa nama"}</h2>
          <div className="mono text-[10px] text-muted">
            {selectedState.road.affectedSupplierIds.map((id) => facilities.get(id) ?? id).join(", ")} →{" "}
            {selectedState.road.affectedWarehouseIds.map((id) => facilities.get(id) ?? id).join(", ")}
          </div>
        </div>
        <button
          type="button"
          onClick={clearSelection}
          aria-label="Tutup detail jalan"
          className="rounded p-1 text-muted transition hover:bg-surface-high hover:text-ink"
        >
          <X size={18} />
        </button>
      </div>

      <div
        className={`my-2.5 inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold ${
          selectedState.road.riskLevel === "critical" || selectedState.road.riskLevel === "high"
            ? "border-danger bg-danger/5 text-danger"
            : selectedState.road.riskLevel === "medium"
            ? "border-warning bg-orange-50 text-warning"
            : "border-primary bg-primary/5 text-primary"
        }`}
      >
        <Waves size={15} /> {formatRisk(selectedState.road.riskLevel)} risiko rute
      </div>

      <dl className="space-y-1.5 text-xs">
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">Risk Band</dt>
          <dd className="font-semibold text-ink">{formatRisk(selectedState.road.riskLevel)}</dd>
        </div>
        {selectedState.road.dynamicRoadRiskScore !== undefined && (
          <div className="flex justify-between border-b border-outline/40 pb-1">
            <dt className="text-muted">Skor Risiko Relatif</dt>
            <dd className="mono font-semibold text-ink">{selectedState.road.dynamicRoadRiskScore.toFixed(2)}</dd>
          </div>
        )}
        {selectedState.road.dynamicRoadRiskScore === undefined && (
          <div className="flex justify-between border-b border-outline/40 pb-1">
            <dt className="text-muted">Estimasi Paparan Historis</dt>
            <dd className="mono font-semibold text-ink">{formatPercent(selectedState.road.riskProbability)}</dd>
          </div>
        )}
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">ID Segmen ResiliChain</dt>
          <dd className="mono font-semibold text-ink">{selectedState.road.segmentId}</dd>
        </div>
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">OSM Way ID</dt>
          <dd className="mono font-semibold text-ink">
            {selectedState.road.osmWayIds && selectedState.road.osmWayIds.length > 0
              ? selectedState.road.osmWayIds.join(", ")
              : "-"}
          </dd>
        </div>
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">Kelas Jalan</dt>
          <dd className="mono font-semibold capitalize text-ink">
            {selectedState.road.highwayClass ?? "unclassified"}
          </dd>
        </div>
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">Perkiraan Keterlambatan</dt>
          <dd
            className={`mono font-semibold ${
              selectedState.road.estimatedDelayMinutes > 0 ? "text-danger" : "text-primary"
            }`}
          >
            +{selectedState.road.estimatedDelayMinutes} mnt
          </dd>
        </div>
        <div className="flex justify-between border-b border-outline/40 pb-1">
          <dt className="text-muted">Model Risk</dt>
          <dd className="mono font-medium text-ink">{selectedState.road.dynamicRoadRiskScore === undefined ? "Historical Flood Exposure v1" : "Scenario-conditioned risk fusion"}</dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-outline/40 pb-1">
          <dt className="text-muted">Faktor Risiko</dt>
          <dd className="text-right font-medium text-ink">
            {selectedState.road.riskFactors.map((x) => x.label).join(", ")}
          </dd>
        </div>
      </dl>
    </div>
  ) : null;

  return (
    <AppShell>
      {!simulationId && (
        <EmptyState
          title="Belum ada simulasi yang dipilih"
          message="Jalankan analisis skenario sebelum membuka analisis gangguan."
        />
      )}
      {simulationId && query.isLoading && <LoadingState label="Memetakan risiko gangguan banjir…" />}
      {query.isError && <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />}
      {query.data && (
        <div className="flex h-[calc(100vh-64px)] min-h-[680px] flex-col xl:flex-row">
          <section className="relative min-h-[520px] flex-1 overflow-hidden bg-surface-low">
            <DisruptionMap
              data={query.data}
              selectedRoadId={selectedState?.road.segmentId}
              selectedCoords={selectedState?.coords}
              onSelectRoad={handleSelect}
              onClearSelection={clearSelection}
              popupContent={popupNode}
            />
            <h1 className="absolute left-4 top-4 rounded-lg border border-outline bg-white/95 px-4 py-2 text-xl font-semibold shadow-sm backdrop-blur">
              Analisis Gangguan
            </h1>
            <div className="absolute bottom-5 left-5 space-y-2">
              {baselineRoute && (
                <div className="card w-max px-4 py-2 text-[10px] font-semibold uppercase">
                  <span className="mr-3 inline-block w-8 border-t-2 border-dashed border-danger align-middle" />
                  Rute normal · {baselineRoute.etaMinutes} mnt · {formatRisk(baselineRoute.floodExposure)} paparan
                </div>
              )}
              {candidateRoute && (
                <div className="card max-w-[520px] px-4 py-2 text-[10px] font-semibold uppercase">
                  <span className="mr-3 inline-block w-8 border-t-2 border-dashed align-middle" style={{ borderColor: CANDIDATE_ROUTE_COLOR }} />
                  {riskAwareCandidateLabel(candidateRoute.floodExposure)} · {candidateRoute.etaMinutes} mnt · {formatRisk(candidateRoute.floodExposure)} paparan
                  {baselineRoute && (
                    <div className="mono ml-11 mt-1 normal-case text-muted">
                      {candidateRoute.etaMinutes - baselineRoute.etaMinutes >= 0 ? "+" : ""}
                      {candidateRoute.etaMinutes - baselineRoute.etaMinutes} menit waktu tempuh
                      {exposureReduction !== null && (
                        <>
                          {" "}
                          · <strong className="text-primary">-{exposureReduction}% proyeksi paparan</strong>
                        </>
                      )}
                    </div>
                  )}
                  <div className="ml-11 mt-1 normal-case text-muted">
                    Generated before recovery optimization; not a selected recovery route.
                  </div>
                </div>
              )}
              <p className="mono text-[10px] text-muted">Skor risiko adalah indikator relatif untuk routing, bukan probabilitas kejadian.</p>
            </div>
          </section>

          <aside className="w-full shrink-0 overflow-y-auto border-l border-outline bg-surface p-6 xl:w-[400px]">
            <div className="mb-5 flex items-center justify-between border-b border-outline pb-4">
              <h2 className="text-lg font-semibold">Dampak Operasional</h2>
              <ShieldAlert className="text-muted" size={20} />
            </div>
            {simulation.data && <ScenarioContextCard simulation={simulation.data} operationalCondition={operationalCondition} />}
            {simulation.data?.modelProvenance && (
              <ModelProvenanceCard provenance={simulation.data.modelProvenance} version={simulation.data.modelVersion} />
            )}
            <div className="grid grid-cols-2 gap-x-4 gap-y-6 border-b border-outline pb-6">
              {[
                ["Segmen Jalan Berisiko", query.data.impact.roadSegmentsAtRisk, Route, true],
                ["Pemasok Terdampak", query.data.impact.impactedSupplierIds.length, Factory, true],
                ["Pesanan Berisiko", query.data.impact.impactedOrderIds.length, ShoppingBag, false],
                [
                  "Perkiraan Paparan Penjualan",
                  formatCompactIdr(query.data.impact.salesExposure.amount),
                  Truck,
                  false,
                ],
              ].map(([label, value, Icon, danger]) => {
                const I = Icon as typeof Route;
                return (
                  <div key={String(label)}>
                    <div className="eyebrow mb-1 flex items-center gap-1">
                      <I size={13} />
                      {String(label)}
                    </div>
                    <div className={`text-[28px] font-semibold leading-none ${danger ? "text-danger" : "text-ink"}`}>
                      {String(value)}
                    </div>
                    <div className="mono mt-1 text-[10px] text-muted">Estimasi simulasi</div>
                  </div>
                );
              })}
            </div>
            <div className="py-6">
              <h3 className="eyebrow mb-3">Masalah Prioritas</h3>
              {query.data.impact.issues.map((issue) => (
                <div
                  key={issue.id}
                  className="flex w-full gap-3 border-b border-outline/50 px-2 py-3 text-left"
                >
                  <AlertTriangle
                    size={19}
                    className={issue.severity === "critical" ? "text-danger shrink-0" : "text-warning shrink-0"}
                  />
                  <span className="flex-1">
                    <span className="mb-1 flex items-center justify-between gap-2">
                      <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${severityClass[issue.severity]}`}>
                        {formatRisk(issue.severity)}
                      </span>
                      <span className="mono text-[10px] font-medium text-ink">{issue.subject}</span>
                    </span>
                    <span className="block text-[13px] leading-snug text-muted">{issue.description}</span>
                  </span>
                </div>
              ))}
            </div>
            <button
              onClick={createPlan}
              disabled={generate.isPending}
              className="mt-auto flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60"
            >
              <Warehouse size={18} />
              {generate.isPending ? "Menyusun rencana terkoordinasi…" : "Buat Rencana Pemulihan"}
              <ArrowRight size={17} />
            </button>
            {generate.isError && <p role="alert" className="mt-2 text-xs text-danger">{generate.error.message}</p>}
          </aside>
        </div>
      )}
    </AppShell>
  );
}
