"use client";

import {
  CheckCircle2, ChevronDown, History, Info, MapPin, Network,
  PackageCheck, Play, RotateCcw, Settings2, Truck, Warehouse, Waves,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState, LoadingState } from "@/components/ui/states";
import type { InventoryOverride, VehicleOverride } from "@/domain/scenario";
import { useRunSimulation, useScenario, useSimulation } from "@/hooks/use-resilichain-data";
import { OperationalConfigDrawer } from "./operational-config-drawer";
import {
  HAZARD_SCENARIOS,
  OPERATIONAL_PRESETS,
  getOperationalPreset,
  type OperationalOverrides,
  type OperationalPreset,
} from "./scenario-presets";

const progressSteps = [
  "Memuat rekaman historis",
  "Mengevaluasi paparan banjir di jalan",
  "Memetakan ketergantungan rantai pasok",
  "Mengidentifikasi pesanan terdampak",
  "Menghasilkan dampak operasional",
];

function countChanges(overrides: OperationalOverrides): number {
  return overrides.vehicleOverrides.length + overrides.inventoryOverrides.length;
}

export function ScenarioPage() {
  const scenario = useScenario();
  const run = useRunSimulation();
  const simulation = useSimulation(run.data?.id ?? "");
  const router = useRouter();

  const [hazardId] = useState("scenario-jakarta-20250304");
  const [opPresetId, setOpPresetId] = useState("normal");
  const [overrides, setOverrides] = useState<OperationalOverrides>(
    OPERATIONAL_PRESETS[0].overrides
  );
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [step, setStep] = useState(-1);

  const selectedHazard = HAZARD_SCENARIOS.find((h) => h.id === hazardId) ?? HAZARD_SCENARIOS[0];
  const selectedPreset = getOperationalPreset(opPresetId);
  const changeCount = countChanges(overrides);

  const handleOpPresetSelect = (preset: OperationalPreset) => {
    setOpPresetId(preset.id);
    setOverrides(preset.overrides);
    setIsCustomMode(false);
    setSelectorOpen(false);
  };

  const handleApplyDrawerOverrides = (newOverrides: OperationalOverrides) => {
    setOverrides(newOverrides);
    setIsCustomMode(true);
  };

  const handleResetToNormal = () => {
    setOpPresetId("normal");
    setOverrides(OPERATIONAL_PRESETS[0].overrides);
    setIsCustomMode(false);
  };

  useEffect(() => {
    if (step < 0 || step >= progressSteps.length) return;
    const timer = window.setTimeout(() => setStep((v) => v + 1), 420);
    return () => window.clearTimeout(timer);
  }, [step]);

  useEffect(() => {
    if (step === progressSteps.length && run.data && simulation.data?.status === "completed") {
      router.push(`/disruption?simulation=${run.data.id}`);
    }
  }, [step, run.data, simulation.data?.status, router]);

  const vehicleSummary = useMemo(() => {
    if (!scenario.data) return { total: 3, available: 3, restricted: 0 };
    const disabledCount = overrides.vehicleOverrides.filter((v: VehicleOverride) => v.available === false).length;
    const restrictedCapCount = overrides.vehicleOverrides.filter((v: VehicleOverride) => v.capacityUnits !== undefined).length;
    const total = scenario.data.vehicles.length;
    return {
      total,
      available: total - disabledCount,
      restricted: restrictedCapCount,
    };
  }, [scenario.data, overrides]);

  const inventorySummary = useMemo(() => {
    const criticalWhEast = overrides.inventoryOverrides.some(
      (inv: InventoryOverride) => inv.facilityId === "wh-east" && inv.quantity < 420
    );
    const criticalWhWest = overrides.inventoryOverrides.some(
      (inv: InventoryOverride) => inv.facilityId === "wh-west" && inv.quantity < 310
    );
    if (criticalWhEast && criticalWhWest) return "Stok Kritis (Semua Gudang)";
    if (criticalWhEast) return "Stok Kritis (Gudang Timur)";
    if (criticalWhWest) return "Stok Kritis (Gudang Barat)";
    return "Persediaan Normal";
  }, [overrides]);

  const counts = useMemo(() => {
    const data = scenario.data;
    if (!data) return null;
    return {
      suppliers: data.facilities.filter((x) => x.kind === "supplier").length,
      factories: data.facilities.filter((x) => x.kind === "factory").length,
      warehouses: data.facilities.filter((x) => x.kind === "warehouse").length,
      stores: data.facilities.filter((x) => x.kind === "store").length,
    };
  }, [scenario.data]);

  const start = () => {
    if (!scenario.data) return;
    setStep(0);
    run.mutate({
      scenarioId: selectedHazard.id,
      vehicleOverrides: overrides.vehicleOverrides.length > 0 ? overrides.vehicleOverrides : undefined,
      inventoryOverrides: overrides.inventoryOverrides.length > 0 ? overrides.inventoryOverrides : undefined,
    });
  };

  return (
    <AppShell>
      <div className="relative p-4 md:p-8">
        {scenario.isLoading && <LoadingState label="Memuat skenario historis…" />}
        {scenario.isError && <ErrorState message={scenario.error.message} onRetry={() => void scenario.refetch()} />}
        {scenario.data && counts && (
          <>
            {/* Page header */}
            <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <h1 className="page-title">Konfigurasi Skenario Rantai Pasok</h1>
                <p className="mt-1 max-w-2xl text-sm text-muted">
                  Pilih skenario bencana dan kondisi operasional bisnis untuk menguji resiliensi rantai pasok.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  id="btn-config-operational"
                  onClick={() => setDrawerOpen(true)}
                  disabled={step >= 0}
                  className="inline-flex items-center gap-2 rounded-lg border border-outline bg-surface px-3 py-2 text-sm font-medium text-muted transition hover:bg-surface-high disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Settings2 size={16} />
                  Atur Data Operasional
                  {changeCount > 0 && (
                    <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold text-white">
                      {changeCount}
                    </span>
                  )}
                </button>
                <button
                  id="btn-run-simulation"
                  onClick={start}
                  disabled={step >= 0 || run.isPending}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Play size={18} fill="currentColor" />
                  Jalankan Simulasi
                </button>
              </div>
            </div>

            {/* Explanatory banner */}
            <div className="mb-6 flex items-start gap-3 rounded-lg border border-outline bg-surface-low p-3.5 text-xs text-muted shadow-sm">
              <Info size={16} className="mt-0.5 text-primary shrink-0" />
              <div>
                <strong>Pemisahan Dimensi Skenario:</strong> Skenario Gangguan menentukan lokasi & risiko paparan banjir jalan, sedangkan Kondisi Operasional menentukan ketersediaan armada dan stok gudang.
              </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
              {/* LEFT: Hazard Scenario selection */}
              <section className="card flex flex-col p-6">
                <div className="mb-4 flex items-center justify-between border-b border-outline pb-3">
                  <div className="flex items-center gap-2">
                    <Waves className="text-primary" size={20} />
                    <h2 className="section-title text-ink">1. Skenario Gangguan (Hazard)</h2>
                  </div>
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase text-primary">
                    {selectedHazard.badge}
                  </span>
                </div>

                <div className="mb-4 rounded-lg border border-outline/70 bg-surface p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-ink text-base">{selectedHazard.name}</h3>
                    <span className="mono text-xs text-muted">{selectedHazard.eventType}</span>
                  </div>
                  <p className="mt-2 text-xs text-muted leading-relaxed">{selectedHazard.description}</p>
                </div>

                <div className="mb-4 grid grid-cols-3 gap-2">
                  <div className="rounded-lg border border-outline/60 bg-surface-low p-3">
                    <div className="eyebrow mb-1">Lokasi</div>
                    <div className="mono flex items-center gap-1 text-xs font-semibold text-ink">
                      <MapPin size={14} className="text-primary" />
                      {selectedHazard.location}
                    </div>
                  </div>
                  <div className="rounded-lg border border-outline/60 bg-surface-low p-3">
                    <div className="eyebrow mb-1">Jenis Peristiwa</div>
                    <div className="mono flex items-center gap-1 text-xs font-semibold text-ink">
                      <Waves size={14} className="text-primary" />
                      {selectedHazard.eventType}
                    </div>
                  </div>
                  <div className="rounded-lg border border-outline/60 bg-surface-low p-3">
                    <div className="eyebrow mb-1">Mode Simulasi</div>
                    <div className="mono flex items-center gap-1 text-xs font-semibold text-ink">
                      <History size={14} className="text-primary" />
                      {selectedHazard.mode}
                    </div>
                  </div>
                </div>

                {/* Map Context Preview Box */}
                <div className="relative mt-auto flex min-h-[190px] overflow-hidden rounded-lg border border-outline bg-[linear-gradient(135deg,#e4edf0,#f5f7f6_45%,#dcebe7)] p-4">
                  <div className="absolute inset-0 opacity-40 [background-image:linear-gradient(#94a3b822_1px,transparent_1px),linear-gradient(90deg,#94a3b822_1px,transparent_1px)] [background-size:24px_24px]" />
                  <div className="relative z-10 m-auto text-center">
                    <MapPin className="mx-auto mb-1.5 text-primary" size={24} />
                    <div className="text-sm font-semibold text-ink">Jaringan Jalan Jakarta & ML Hazard Risk</div>
                    <div className="mono text-[10px] text-muted">1,413 Segmen Dianalisis · Model Historis v1</div>
                  </div>
                </div>
              </section>

              {/* RIGHT: Operational Condition selection */}
              <section className="card flex flex-col p-6">
                <div className="mb-4 flex items-center justify-between border-b border-outline pb-3">
                  <div className="flex items-center gap-2">
                    <Network className="text-primary" size={20} />
                    <h2 className="section-title text-ink">2. Kondisi Operasional Bisnis</h2>
                  </div>
                  {isCustomMode && (
                    <button
                      onClick={handleResetToNormal}
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      <RotateCcw size={12} /> Reset Normal
                    </button>
                  )}
                </div>

                {/* Operational Preset Dropdown Selector */}
                <div className="mb-4">
                  <div className="eyebrow mb-2">Preset Kondisi Operasional</div>
                  <div className="relative">
                    <button
                      id="btn-op-selector"
                      aria-haspopup="listbox"
                      aria-expanded={selectorOpen}
                      onClick={() => setSelectorOpen((v) => !v)}
                      className="flex w-full items-center justify-between rounded-lg border border-outline bg-surface px-3.5 py-3 text-sm font-medium transition hover:bg-surface-high"
                    >
                      <span className="flex items-center gap-2.5">
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                            isCustomMode
                              ? "bg-amber-600 text-white"
                              : selectedPreset.badge === "DEFAULT"
                              ? "bg-primary text-white"
                              : selectedPreset.badge === "MODERAT"
                              ? "bg-teal-700 text-white"
                              : selectedPreset.badge === "SEDANG"
                              ? "bg-amber-700 text-white"
                              : "bg-danger text-white"
                          }`}
                        >
                          {isCustomMode ? "KUSTOM" : selectedPreset.badge}
                        </span>
                        <span className="font-semibold text-ink">
                          {isCustomMode ? "Kondisi Disesuaikan (Kustom)" : selectedPreset.label}
                        </span>
                      </span>
                      <ChevronDown
                        size={16}
                        className={`text-muted transition-transform ${selectorOpen ? "rotate-180" : ""}`}
                      />
                    </button>
                    {selectorOpen && (
                      <ul
                        role="listbox"
                        aria-label="Pilih kondisi operasional"
                        className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-outline bg-surface shadow-xl"
                      >
                        {OPERATIONAL_PRESETS.map((preset) => (
                          <li
                            key={preset.id}
                            role="option"
                            aria-selected={preset.id === opPresetId && !isCustomMode}
                            onClick={() => handleOpPresetSelect(preset)}
                            className={`flex cursor-pointer items-center gap-3 px-4 py-3 text-sm transition hover:bg-surface-high ${
                              preset.id === opPresetId && !isCustomMode ? "bg-primary/10 font-semibold" : ""
                            }`}
                          >
                            <span
                              className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                                preset.badge === "DEFAULT"
                                  ? "bg-primary text-white"
                                  : preset.badge === "MODERAT"
                                  ? "bg-teal-700 text-white"
                                  : preset.badge === "SEDANG"
                                  ? "bg-amber-700 text-white"
                                  : "bg-danger text-white"
                              }`}
                            >
                              {preset.badge}
                            </span>
                            <div className="flex-1">
                              <div className="font-semibold text-ink">{preset.label}</div>
                              <div className="text-xs text-muted">{preset.description}</div>
                            </div>
                            {preset.id === opPresetId && !isCustomMode && (
                              <CheckCircle2 size={16} className="text-primary shrink-0" />
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Preset explanation box */}
                  <div className="mt-3 rounded-lg border border-outline/70 bg-surface-low p-3.5 text-xs leading-relaxed text-muted">
                    {isCustomMode
                      ? "Parameter operasional telah disesuaikan secara kustom via panel Atur Data Operasional."
                      : selectedPreset.description}
                  </div>
                </div>

                {/* Live Operational Status Cards */}
                <div className="mb-4 grid grid-cols-3 gap-2">
                  <div className="rounded-lg border border-outline/60 bg-surface p-3 text-center">
                    <div className="eyebrow mb-1 flex items-center justify-center gap-1">
                      <Truck size={13} /> Kendaraan
                    </div>
                    <div className="text-sm font-semibold text-ink">
                      {vehicleSummary.available} / {vehicleSummary.total} Tersedia
                    </div>
                    {vehicleSummary.restricted > 0 && (
                      <div className="mono mt-0.5 text-[10px] text-amber-700 font-medium">Kapasitas dibatasi</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-outline/60 bg-surface p-3 text-center">
                    <div className="eyebrow mb-1 flex items-center justify-center gap-1">
                      <Warehouse size={13} /> Persediaan
                    </div>
                    <div className="text-sm font-semibold text-ink">{inventorySummary}</div>
                  </div>
                  <div className="rounded-lg border border-outline/60 bg-surface p-3 text-center">
                    <div className="eyebrow mb-1 flex items-center justify-center gap-1">
                      <PackageCheck size={13} /> Pesanan
                    </div>
                    <div className="text-sm font-semibold text-ink">20 Pesanan Aktif</div>
                  </div>
                </div>

                {/* Network nodes summary */}
                <div className="mt-auto grid grid-cols-4 gap-2 rounded-lg border border-outline/60 bg-surface-low p-3 text-center text-xs">
                  <div>
                    <div className="mono font-semibold text-ink">2</div>
                    <div className="eyebrow text-[9px]">Pemasok</div>
                  </div>
                  <div>
                    <div className="mono font-semibold text-ink">1</div>
                    <div className="eyebrow text-[9px]">Pabrik</div>
                  </div>
                  <div>
                    <div className="mono font-semibold text-ink">2</div>
                    <div className="eyebrow text-[9px]">Gudang</div>
                  </div>
                  <div>
                    <div className="mono font-semibold text-ink">5</div>
                    <div className="eyebrow text-[9px]">Toko</div>
                  </div>
                </div>
              </section>
            </div>
          </>
        )}

        {(run.isError || simulation.data?.status === "failed") && (
          <p role="alert" className="mb-4 mt-4 text-sm text-danger">
            {run.error?.message ?? simulation.data?.error?.message ?? "Simulasi gagal."}
          </p>
        )}

        {/* Progress overlay */}
        {step >= 0 &&
          (step < progressSteps.length ||
            simulation.data?.status === "queued" ||
            simulation.data?.status === "processing") && (
            <div
              className="fixed inset-0 z-[70] grid place-items-center bg-background/80 p-4 backdrop-blur-sm"
              role="status"
              aria-live="polite"
            >
              <div className="card w-full max-w-sm p-6 text-center shadow-2xl">
                <Network className="mx-auto mb-3 animate-pulse text-primary" size={32} />
                <h2 className="section-title">Menganalisis Dampak & Simulasi…</h2>
                <p className="my-4 text-sm text-muted">{progressSteps[step] ?? "Menunggu pemrosesan backend"}</p>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-high">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-300"
                    style={{ width: `${Math.min(((step + 1) / progressSteps.length) * 100, 100)}%` }}
                  />
                </div>
                <div className="mono mt-2 text-[10px] text-muted">
                  {step < progressSteps.length
                    ? `Langkah ${step + 1} dari ${progressSteps.length}`
                    : "Pemrosesan backend"}
                </div>
              </div>
            </div>
          )}
      </div>

      {/* Operational config drawer */}
      {scenario.data && (
        <OperationalConfigDrawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          scenario={scenario.data}
          preset={selectedPreset}
          overrides={overrides}
          onApply={handleApplyDrawerOverrides}
        />
      )}
    </AppShell>
  );
}
