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
      <h2 id="weather-title" className="mb-3 text-center text-[24px] font-bold text-primary-dark md:text-[32px]">
        SIMULASI CUACA
      </h2>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4" role="radiogroup" aria-label="Pola curah hujan">
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
              className={`min-h-[150px] rounded-[28px] p-5 text-left shadow-[0_0_7px_rgb(0_0_0/25%)] transition md:min-h-[183px] md:px-4 md:py-6 ${selected ? activeWeatherStyles[scenario.id] : "bg-white text-black hover:-translate-y-0.5"}`}
            >
              <span className="block text-[20px] font-bold leading-[1.08] md:text-[25px]">{scenario.label}</span>
              <span className="mt-4 block text-[12px] font-medium leading-[1.35] md:text-[14px]">{scenario.description}</span>
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
        className={`mt-3 flex min-h-[58px] w-full items-center justify-between rounded-[28px] px-7 text-left text-[18px] font-bold text-primary shadow-[0_0_7px_rgb(0_0_0/20%)] transition md:text-[22px] ${analysisMode === "historical-replay" ? "bg-primary-soft" : "bg-white hover:bg-surface-low"}`}
      >
        <span>Gunakan Data Simulasi Historis</span>
        <History className="h-7 w-7 shrink-0" aria-hidden="true" />
      </button>
    </section>
  );
}
