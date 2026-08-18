"use client";

import { Info, Network, Play, Settings2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState, LoadingState } from "@/components/ui/states";
import type { BusinessImportResponse } from "@/domain/business-data";
import type { AnalysisMode, RainfallScenario, RunSimulationRequest } from "@/domain/scenario";
import { useImportBusinessData, useRunSimulation, useScenario, useSimulation } from "@/hooks/use-resilichain-data";
import { ApiError } from "@/lib/api-client";
import { AnalysisModePanel } from "./analysis-mode-panel";
import { BusinessDataPanel } from "./business-data-panel";
import { OperationalConditionPanel } from "./operational-condition-panel";
import { OperationalConfigDrawer } from "./operational-config-drawer";
import {
  OPERATIONAL_PRESETS,
  getOperationalPreset,
  type OperationalOverrides,
  type OperationalPreset,
} from "./scenario-presets";

const progressSteps = [
  "Memuat konteks analisis",
  "Mengevaluasi risiko relatif koridor",
  "Menghitung rute rantai pasok",
  "Mengidentifikasi dampak operasional",
  "Menyiapkan hasil analisis",
];

function countChanges(overrides: OperationalOverrides): number {
  return overrides.vehicleOverrides.length + overrides.inventoryOverrides.length;
}

export function ScenarioPage() {
  const scenario = useScenario();
  const run = useRunSimulation();
  const businessImport = useImportBusinessData();
  const router = useRouter();
  const [activeSimulationId, setActiveSimulationId] = useState("");
  const simulation = useSimulation(activeSimulationId);

  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("historical-replay");
  const [rainfallScenario, setRainfallScenario] = useState<RainfallScenario>();
  const [opPresetId, setOpPresetId] = useState("normal");
  const [overrides, setOverrides] = useState<OperationalOverrides>(OPERATIONAL_PRESETS[0].overrides);
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [businessMode, setBusinessMode] = useState<"demo" | "custom">("demo");
  const [businessPreview, setBusinessPreview] = useState<BusinessImportResponse>();
  const [businessSnapshotId, setBusinessSnapshotId] = useState("");
  const [step, setStep] = useState(-1);

  const selectedPreset = getOperationalPreset(opPresetId);
  const busy = step >= 0 || run.isPending;
  const businessReady = businessMode === "demo" || Boolean(businessSnapshotId);
  const simulationReady = businessReady && (analysisMode === "historical-replay" || rainfallScenario !== undefined);

  const clearPreviousResult = () => {
    run.reset();
    setActiveSimulationId("");
    setStep(-1);
  };

  const handleModeChange = (mode: AnalysisMode) => {
    setAnalysisMode(mode);
    clearPreviousResult();
  };

  const handleRainfallChange = (value: RainfallScenario) => {
    setRainfallScenario(value);
    clearPreviousResult();
  };

  const handleOpPresetSelect = (preset: OperationalPreset) => {
    setOpPresetId(preset.id);
    setOverrides(preset.overrides);
    setIsCustomMode(false);
    clearPreviousResult();
  };

  const handleApplyDrawerOverrides = (newOverrides: OperationalOverrides) => {
    setOverrides(newOverrides);
    setIsCustomMode(true);
    clearPreviousResult();
  };

  const handleResetToNormal = () => {
    setOpPresetId("normal");
    setOverrides(OPERATIONAL_PRESETS[0].overrides);
    setIsCustomMode(false);
    clearPreviousResult();
  };

  const handleBusinessModeChange = (mode: "demo" | "custom") => {
    setBusinessMode(mode);
    clearPreviousResult();
  };

  const handleBusinessUpload = async (file: File) => {
    businessImport.reset();
    setBusinessSnapshotId("");
    clearPreviousResult();
    try {
      setBusinessPreview(await businessImport.mutateAsync(file));
    } catch {
      setBusinessPreview(undefined);
    }
  };

  const handleBusinessConfirm = () => {
    if (!businessPreview) return;
    setBusinessSnapshotId(businessPreview.businessSnapshotId);
    clearPreviousResult();
  };

  useEffect(() => {
    if (step < 0 || step >= progressSteps.length) return;
    const timer = window.setTimeout(() => setStep((value) => value + 1), 420);
    return () => window.clearTimeout(timer);
  }, [step]);

  useEffect(() => {
    if (step !== progressSteps.length || simulation.data?.status !== "completed") return;
    const params = new URLSearchParams({
      simulation: simulation.data.id,
      condition: isCustomMode ? "custom" : opPresetId,
    });
    router.push(`/disruption?${params.toString()}`);
  }, [isCustomMode, opPresetId, router, simulation.data, step]);

  const start = async () => {
    if (!scenario.data || !simulationReady) return;
    clearPreviousResult();
    setStep(0);
    try {
      const operationalOverrides = {
        businessSnapshotId: businessMode === "custom" ? businessSnapshotId : undefined,
        vehicleOverrides: overrides.vehicleOverrides.length > 0 ? overrides.vehicleOverrides : undefined,
        inventoryOverrides: overrides.inventoryOverrides.length > 0 ? overrides.inventoryOverrides : undefined,
      };
      const request: RunSimulationRequest = analysisMode === "scenario-simulation" && rainfallScenario !== undefined ? {
        scenarioId: scenario.data.id,
        analysisMode: "scenario-simulation",
        region: "jakarta",
        rainfallScenario,
        ...operationalOverrides,
      } : {
        scenarioId: scenario.data.id,
        analysisMode: "historical-replay",
        ...operationalOverrides,
      };
      const result = await run.mutateAsync(request);
      setActiveSimulationId(result.id);
    } catch (error) {
      if (error instanceof ApiError && error.code === "BUSINESS_SNAPSHOT_NOT_FOUND") {
        setBusinessSnapshotId("");
        setBusinessPreview(undefined);
      }
      setStep(-1);
    }
  };

  return (
    <AppShell>
      <div className="relative p-4 md:p-8">
        {scenario.isLoading && <LoadingState label="Memuat skenario Jakarta…" />}
        {scenario.isError && <ErrorState message={scenario.error.message} onRetry={() => void scenario.refetch()} />}
        {scenario.data && (
          <>
            <header className="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
              <div>
                <div className="eyebrow mb-1">Analisis Risiko</div>
                <h1 className="page-title">Konfigurasi Skenario Rantai Pasok</h1>
                <p className="mt-1 max-w-2xl text-sm text-muted">ResiliChain mengevaluasi bagaimana risiko lingkungan berinteraksi dengan kondisi operasional perusahaan.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" id="btn-config-operational" onClick={() => setDrawerOpen(true)} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-outline bg-surface px-3 py-2 text-sm font-medium text-muted transition hover:bg-surface-high disabled:opacity-50">
                  <Settings2 size={16} /> Atur Data Operasional
                  {countChanges(overrides) > 0 && <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold text-white">{countChanges(overrides)}</span>}
                </button>
                <button type="button" id="btn-run-simulation" onClick={() => void start()} disabled={busy || !simulationReady} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50">
                  <Play size={18} fill="currentColor" /> Jalankan Analisis
                </button>
              </div>
            </header>

            <div className="mb-6 flex items-start gap-3 rounded-lg border border-outline bg-surface-low p-3.5 text-xs leading-relaxed text-muted shadow-sm">
              <Info size={16} className="mt-0.5 shrink-0 text-primary" />
              <span><strong className="text-ink">Dua dimensi independen:</strong> kondisi lingkungan menentukan konteks risiko jalan; kondisi operasional menentukan armada dan persediaan. Keduanya digabungkan saat analisis dijalankan.</span>
            </div>

            <BusinessDataPanel
              mode={businessMode}
              preview={businessPreview}
              activeSnapshotId={businessSnapshotId}
              pending={businessImport.isPending}
              error={businessImport.error}
              disabled={busy}
              onModeChange={handleBusinessModeChange}
              onUpload={(file) => void handleBusinessUpload(file)}
              onConfirm={handleBusinessConfirm}
            />

            <div className="grid gap-6 xl:grid-cols-2">
              <AnalysisModePanel analysisMode={analysisMode} rainfallScenario={rainfallScenario} disabled={busy} onModeChange={handleModeChange} onRainfallChange={handleRainfallChange} />
              <OperationalConditionPanel scenario={scenario.data} selectedPresetId={opPresetId} overrides={overrides} custom={isCustomMode} disabled={busy} onSelect={handleOpPresetSelect} onReset={handleResetToNormal} />
            </div>

            {analysisMode === "scenario-simulation" && rainfallScenario === undefined && (
              <p className="mt-4 text-sm text-muted" role="status">Pilih satu pola curah hujan untuk menjalankan simulasi kondisi.</p>
            )}
          </>
        )}

        {(run.isError || simulation.isError || simulation.data?.status === "failed") && (
          <ErrorState
            message={run.error?.message ?? simulation.error?.message ?? simulation.data?.error?.message ?? "Simulasi tidak dapat diselesaikan."}
            onRetry={simulation.isError ? () => void simulation.refetch() : simulationReady ? () => void start() : undefined}
          />
        )}

        {step >= 0 && (step < progressSteps.length || simulation.data?.status === "queued" || simulation.data?.status === "processing") && (
          <div className="fixed inset-0 z-[70] grid place-items-center bg-background/80 p-4 backdrop-blur-sm" role="status" aria-live="polite">
            <div className="card w-full max-w-sm p-6 text-center shadow-2xl">
              <Network className="mx-auto mb-3 animate-pulse text-primary" size={32} />
              <h2 className="section-title">Menganalisis Skenario…</h2>
              <p className="my-4 text-sm text-muted">{progressSteps[step] ?? "Menunggu pemrosesan backend"}</p>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-high"><div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${Math.min(((step + 1) / progressSteps.length) * 100, 100)}%` }} /></div>
            </div>
          </div>
        )}
      </div>

      {scenario.data && <OperationalConfigDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} scenario={scenario.data} preset={selectedPreset} overrides={overrides} onApply={handleApplyDrawerOverrides} />}
    </AppShell>
  );
}
