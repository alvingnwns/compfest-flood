import { CheckCircle2, CloudRain, History, MapPin } from "lucide-react";
import type { AnalysisMode, RainfallScenario } from "@/domain/scenario";
import { HAZARD_SCENARIOS, RAINFALL_SCENARIOS } from "./scenario-presets";

export function AnalysisModePanel({
  analysisMode,
  rainfallScenario,
  disabled,
  onModeChange,
  onRainfallChange,
}: {
  analysisMode: AnalysisMode;
  rainfallScenario?: RainfallScenario;
  disabled?: boolean;
  onModeChange: (mode: AnalysisMode) => void;
  onRainfallChange: (scenario: RainfallScenario) => void;
}) {
  const historical = HAZARD_SCENARIOS[0];
  return (
    <section className="card flex flex-col p-5 md:p-6">
      <div className="mb-4 flex items-center gap-2 border-b border-outline pb-3">
        <CloudRain className="text-primary" size={20} />
        <h2 className="section-title text-ink">1. Kondisi Lingkungan</h2>
      </div>
      <fieldset disabled={disabled}>
        <legend className="eyebrow mb-2">Mode Analisis</legend>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Mode analisis">
          {([
            ["scenario-simulation", "Simulasi Kondisi", CloudRain],
            ["historical-replay", "Pemutaran Ulang Historis", History],
          ] as const).map(([value, label, Icon]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={analysisMode === value}
              onClick={() => onModeChange(value)}
              className={`flex min-h-11 items-center justify-between rounded-lg border px-3 py-2 text-left text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${analysisMode === value ? "border-primary bg-primary/10 text-primary" : "border-outline bg-surface hover:bg-surface-high"}`}
            >
              <span className="flex items-center gap-2"><Icon size={16} /> {label}</span>
              {analysisMode === value && <CheckCircle2 size={16} />}
            </button>
          ))}
        </div>
      </fieldset>

      {analysisMode === "scenario-simulation" ? (
        <div className="mt-5">
          <div className="mb-4 rounded-lg border border-outline/70 bg-surface-low p-3 text-xs">
            <span className="eyebrow mr-2">Wilayah</span>
            <strong className="inline-flex items-center gap-1 text-ink"><MapPin size={13} /> Jakarta</strong>
          </div>
          <fieldset disabled={disabled}>
            <legend className="eyebrow mb-2">Pola Curah Hujan</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {RAINFALL_SCENARIOS.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  role="radio"
                  aria-checked={rainfallScenario === scenario.id}
                  onClick={() => onRainfallChange(scenario.id)}
                  className={`rounded-lg border p-3 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${rainfallScenario === scenario.id ? "border-primary bg-primary/10" : "border-outline bg-surface hover:bg-surface-high"}`}
                >
                  <span className="block text-sm font-semibold text-ink">{scenario.label}</span>
                  <span className="mt-1 block text-xs leading-relaxed text-muted">{scenario.description}</span>
                </button>
              ))}
            </div>
          </fieldset>
          <p className="mt-3 text-xs leading-relaxed text-muted">Representasi pola temporal 30 hari yang diturunkan dari data historis.</p>
        </div>
      ) : (
        <div className="mt-5 rounded-lg border border-outline bg-surface-low p-4">
          <div className="flex items-start justify-between gap-3">
            <div><h3 className="font-semibold text-ink">{historical.name}</h3><p className="mt-1 text-xs text-muted">{historical.description}</p></div>
            <span className="rounded bg-primary/10 px-2 py-1 text-[10px] font-bold text-primary">HISTORIS</span>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs font-medium text-ink"><MapPin size={14} className="text-primary" /> Jakarta · 04 Mar 2025</div>
        </div>
      )}
    </section>
  );
}
