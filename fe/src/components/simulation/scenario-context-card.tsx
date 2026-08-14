import { CloudRain, Factory, Info, MapPin } from "lucide-react";
import type { Simulation } from "@/domain/scenario";
import { getOperationalPreset, getRainfallScenario } from "@/features/scenario/scenario-presets";

export function operationalConditionLabel(id?: string): string {
  if (id === "custom") return "Kondisi Disesuaikan";
  return getOperationalPreset(id ?? "normal").label;
}

export function ScenarioContextCard({
  simulation,
  operationalCondition,
  explanation = false,
}: {
  simulation: Simulation;
  operationalCondition?: string;
  explanation?: boolean;
}) {
  const dynamic = simulation.analysisMode === "scenario-simulation" && simulation.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.hazard?.rainfallScenario) : undefined;

  return (
    <section className="mb-5 rounded-lg border border-outline bg-surface-low p-4" aria-label="Konteks analisis">
      <div className="mb-3 flex items-center gap-2">
        <Info size={16} className="text-primary" />
        <h2 className="text-sm font-semibold text-ink">Konteks Analisis</h2>
      </div>
      <dl className="grid gap-3 text-xs sm:grid-cols-2">
        <div>
          <dt className="eyebrow mb-1 flex items-center gap-1"><CloudRain size={12} /> Kondisi Lingkungan</dt>
          <dd className="font-semibold text-ink">
            {dynamic ? rainfall?.label ?? "Pola Curah Hujan" : "Jakarta — 04 Mar 2025"}
          </dd>
          <dd className="mt-0.5 text-muted">{dynamic ? "Simulasi Kondisi" : "Pemutaran Ulang Historis"}</dd>
        </div>
        <div>
          <dt className="eyebrow mb-1 flex items-center gap-1"><Factory size={12} /> Kondisi Operasional</dt>
          <dd className="font-semibold text-ink">{operationalConditionLabel(operationalCondition)}</dd>
          <dd className="mt-0.5 flex items-center gap-1 text-muted"><MapPin size={11} /> Jakarta</dd>
        </div>
      </dl>
      {dynamic && (
        <p className="mt-3 border-t border-outline/60 pt-3 text-xs leading-relaxed text-muted">
          Risiko jalan dikondisikan oleh pola temporal hujan yang dipilih dan kerentanan historis masing-masing koridor.
        </p>
      )}
      {dynamic && explanation && (
        <div className="mt-3 rounded-md border border-primary/15 bg-primary/5 p-3 text-xs leading-relaxed text-muted">
          <strong className="text-ink">Mengapa hasil dapat berubah?</strong> Pola hujan mengubah risiko relatif koridor; sistem lalu menghitung ulang rute dan keputusan operasional. Sebagian risiko dapat diserap oleh kapasitas, inventori, atau rute alternatif sehingga keputusan akhir tidak selalu berubah.
        </div>
      )}
    </section>
  );
}
