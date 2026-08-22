"use client";

import { Network, Play, RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState, LoadingState } from "@/components/ui/states";
import type { BusinessImportResponse } from "@/domain/business-data";
import type { AnalysisMode, RainfallScenario, RunSimulationRequest } from "@/domain/scenario";
import { useImportBusinessData, useRunSimulation, useScenario, useSimulation } from "@/hooks/use-aruna-data";
import { ApiError } from "@/lib/api-client";
import { AnalysisModePanel } from "./analysis-mode-panel";
import { BusinessDataPanel } from "./business-data-panel";
import { OperationalConditionPanel } from "./operational-condition-panel";
import { OperationalEditor } from "./operational-editor";
import {
  type BusinessDataMode,
  showsEnvironmentalCondition,
  showsOperationalFlow,
  showsWeatherSimulation,
} from "./scenario-flow";
import {
  DEFAULT_OPERATIONAL_PRESET,
  OPERATIONAL_PRESETS,
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

export function ScenarioPage() {
  const scenario = useScenario();
  const run = useRunSimulation();
  const businessImport = useImportBusinessData();
  const router = useRouter();
  const [activeSimulationId, setActiveSimulationId] = useState("");
  const simulation = useSimulation(activeSimulationId);

  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("scenario-simulation");
  const [rainfallScenario, setRainfallScenario] = useState<RainfallScenario>("Q1");
  const [opPresetId, setOpPresetId] = useState(DEFAULT_OPERATIONAL_PRESET.id);
  const [overrides, setOverrides] = useState<OperationalOverrides>(DEFAULT_OPERATIONAL_PRESET.overrides);
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [businessMode, setBusinessMode] = useState<BusinessDataMode>();
  const [businessPreview, setBusinessPreview] = useState<BusinessImportResponse>();
  const [businessSnapshotId, setBusinessSnapshotId] = useState("");
  const [step, setStep] = useState(-1);

  const busy = step >= 0 || run.isPending;
  const businessReady = businessMode === "demo" || (businessMode === "custom" && Boolean(businessSnapshotId));
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
    setOpPresetId(DEFAULT_OPERATIONAL_PRESET.id);
    setOverrides(DEFAULT_OPERATIONAL_PRESET.overrides);
    setIsCustomMode(false);
    clearPreviousResult();
  };

  const handleResetToDefault = () => {
    setAnalysisMode("scenario-simulation");
    setRainfallScenario("Q1");
    setBusinessMode(undefined);
    setBusinessPreview(undefined);
    setBusinessSnapshotId("");
    handleResetToNormal();
  };

  const handleBusinessModeChange = (mode: BusinessDataMode) => {
    setBusinessMode(mode);
    setAnalysisMode("scenario-simulation");
    setRainfallScenario("Q1");
    if (mode === "demo") {
      setBusinessSnapshotId("");
      setBusinessPreview(undefined);
      setIsCustomMode(false);
      const activePreset = OPERATIONAL_PRESETS.find((p) => p.id === opPresetId) ?? OPERATIONAL_PRESETS[0];
      setOverrides(activePreset.overrides);
    }
    clearPreviousResult();
  };

  const handleBusinessUpload = async (file: File) => {
    businessImport.reset();
    setBusinessSnapshotId("");
    clearPreviousResult();
    try {
      const preview = await businessImport.mutateAsync(file);
      setBusinessPreview(preview);
      setBusinessSnapshotId(preview.businessSnapshotId);
      setIsCustomMode(false);
    } catch {
      setBusinessPreview(undefined);
      setBusinessSnapshotId("");
    }
  };

  const handleBusinessConfirm = () => {
    if (!businessPreview) return;
    setBusinessSnapshotId(businessPreview.businessSnapshotId);
    setIsCustomMode(false);
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
        customVehicles:
          overrides.customVehicles && overrides.customVehicles.length > 0
            ? overrides.customVehicles
            : undefined,
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
    <AppShell
      title="Skenario"
      actions={
        <>
          <button
            type="button"
            onClick={handleResetToDefault}
            disabled={busy}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-[12px] bg-primary-dark px-4 text-[13px] font-semibold text-white transition hover:brightness-110 disabled:opacity-50 md:h-11 md:px-5 md:text-[14px]"
          >
            <RefreshCcw className="h-4 w-4 shrink-0" />
            <span className="hidden sm:inline">Kembalikan ke Default</span>
          </button>
          <button
            type="button"
            id="btn-run-simulation"
            onClick={() => void start()}
            disabled={busy || !simulationReady}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-[12px] bg-gradient-to-r from-[#eba92d] to-[#ffa600] px-5 text-[13px] font-bold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50 md:h-11 md:px-6 md:text-[14px]"
          >
            <Play className="h-4 w-4 shrink-0" fill="none" />
            <span className="hidden sm:inline">Jalankan Analisis</span>
          </button>
        </>
      }
    >
      <div
        className={`scenario-pattern relative min-h-[calc(100vh-80px)] px-4 py-8 md:px-8 md:py-10 ${
          scenario.data && businessMode === undefined ? "grid place-items-center" : ""
        }`}
      >
        {scenario.isLoading && <LoadingState label="Memuat skenario Jakarta…" />}
        {scenario.isError && <ErrorState message={scenario.error.message} onRetry={() => void scenario.refetch()} />}
        {scenario.data && (
          <div className="mx-auto max-w-[1456px] space-y-12">
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
            {showsOperationalFlow(businessMode) && (
              <>
                {showsWeatherSimulation(businessMode) && (
                  <AnalysisModePanel analysisMode={analysisMode} rainfallScenario={rainfallScenario} disabled={busy} onModeChange={handleModeChange} onRainfallChange={handleRainfallChange} />
                )}
                {showsEnvironmentalCondition(businessMode) && (
                  <OperationalConditionPanel scenario={scenario.data} selectedPresetId={opPresetId} overrides={overrides} custom={isCustomMode} disabled={busy} onSelect={handleOpPresetSelect} onReset={handleResetToNormal} />
                )}
                <OperationalEditor
                  key={`${opPresetId}:${businessSnapshotId}`}
                  scenario={scenario.data}
                  overrides={overrides}
                  presetId={opPresetId}
                  custom={isCustomMode}
                  businessData={businessMode === "custom" ? businessPreview : undefined}
                  disabled={busy}
                  onChange={handleApplyDrawerOverrides}
                />
              </>
            )}
          </div>
        )}

        {(run.error || simulation.isError || simulation.data?.status === "failed") && (
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

    </AppShell>
  );
}
