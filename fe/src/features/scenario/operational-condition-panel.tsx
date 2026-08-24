import type { Scenario } from "@/domain/scenario";
import { OPERATIONAL_PRESETS, type OperationalOverrides, type OperationalPreset } from "./scenario-presets";

const visualOrder = ["normal", "severe-disruption", "limited-vehicle", "critical-stock"];

const figmaDescriptions: Record<string, string> = {
  normal: "Operasional berjalan lancar.",
  "severe-disruption": "Keterbatasan kendaraan dan stok.",
  "limited-vehicle": "Sebagian kendaraan tidak tersedia.",
  "critical-stock": "Persediaan gudang mulai menipis.",
};

export function OperationalConditionPanel({
  selectedPresetId,
  custom,
  disabled,
  onSelect,
}: {
  scenario: Scenario;
  selectedPresetId: string;
  overrides: OperationalOverrides;
  custom: boolean;
  disabled?: boolean;
  onSelect: (preset: OperationalPreset) => void;
  onReset: () => void;
}) {
  const presets = visualOrder.map((id) => OPERATIONAL_PRESETS.find((preset) => preset.id === id)!);

  return (
    <section aria-labelledby="condition-title" className="mx-auto w-full max-w-[1504px]">
      <h2 id="condition-title" className="mb-3 text-center text-[20px] font-bold text-primary-dark md:text-[22px]">
        KONDISI LINGKUNGAN
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" role="radiogroup" aria-label="Kondisi operasional">
        {presets.map((preset) => {
          const selected = !custom && selectedPresetId === preset.id;
          const title = preset.id === "severe-disruption" ? "Gangguan Operasional" : preset.label;
          return (
            <button
              key={preset.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onSelect(preset)}
              className={`relative min-h-[80px] rounded-[18px] px-4 py-3 text-left shadow-sm transition ${selected ? "bg-primary-dark text-white" : "bg-white text-primary hover:-translate-y-0.5"}`}
            >
              <span className="block pr-6 text-[15px] font-bold leading-tight md:text-[16px]">{title}</span>
              <span className="mt-1 block pr-4 text-[11px] font-medium leading-snug md:text-[12px] opacity-80">{figmaDescriptions[preset.id]}</span>
              <span className={`absolute right-3 top-3 grid h-5 w-5 place-items-center rounded-full border ${selected ? "border-white" : "border-primary/60"}`} aria-hidden="true">
                {selected && <span className="h-2 w-2 rounded-full bg-white" />}
              </span>
            </button>
          );
        })}
      </div>
      {custom && <p className="mt-3 text-center text-sm font-semibold text-primary">Konfigurasi operasional disesuaikan secara manual.</p>}
    </section>
  );
}
