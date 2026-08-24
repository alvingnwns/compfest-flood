import { History } from "lucide-react";
import type { AnalysisMode, RainfallScenario } from "@/domain/scenario";
import { RAINFALL_SCENARIOS } from "./scenario-presets";

const activeWeatherStyles: Record<RainfallScenario, string> = {
  Q1: "bg-gradient-to-br from-[#72ee8d] to-[#00b98e] text-black",
  Q2: "bg-gradient-to-br from-[#ffd36c] to-[#ffa718] text-black",
  Q3: "bg-gradient-to-br from-[#ff956c] to-[#f13024] text-black",
  Q4: "bg-gradient-to-br from-[#aa0ac7] to-[#37003f] text-white",
};

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
  const chooseRainfall = (value: RainfallScenario) => {
    onModeChange("scenario-simulation");
    onRainfallChange(value);
  };

  return (
    <section aria-labelledby="weather-title" className="mx-auto w-full max-w-[1308px]">
      <h2 id="weather-title" className="mb-3 text-center text-[20px] font-bold text-primary-dark md:text-[22px]">
        SIMULASI CUACA
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="radiogroup" aria-label="Pola curah hujan">
        {RAINFALL_SCENARIOS.map((scenario) => {
          const selected = analysisMode === "scenario-simulation" && rainfallScenario === scenario.id;
          return (
            <button
              key={scenario.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => chooseRainfall(scenario.id)}
              className={`min-h-[135px] rounded-[20px] p-4 text-left shadow-sm transition md:min-h-[150px] md:p-5 ${selected ? activeWeatherStyles[scenario.id] : "bg-white text-black hover:-translate-y-0.5"}`}
            >
              <span className="block text-[16px] font-bold leading-[1.15] md:text-[18px]">{scenario.label}</span>
              <span className="mt-2.5 block text-[12px] font-medium leading-[1.35] md:text-[13px]">{scenario.description}</span>
            </button>
          );
        })}
      </div>
      <button
        type="button"
        role="radio"
        aria-checked={analysisMode === "historical-replay"}
        disabled={disabled}
        onClick={() => onModeChange("historical-replay")}
        className={`mt-3 flex min-h-[48px] w-full items-center justify-between rounded-[20px] px-6 text-left text-[15px] font-bold text-primary shadow-sm transition md:text-[16px] ${analysisMode === "historical-replay" ? "bg-primary-soft" : "bg-white hover:bg-surface-low"}`}
      >
        <span>Gunakan Data Simulasi Historis</span>
        <History className="h-5 w-5 shrink-0" aria-hidden="true" />
      </button>
    </section>
  );
}
