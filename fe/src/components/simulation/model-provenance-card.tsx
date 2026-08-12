import { BrainCircuit, Database, MapPinned } from "lucide-react";
import type { Simulation } from "@/domain/scenario";

type Provenance = NonNullable<Simulation["modelProvenance"]>;

export function ModelProvenanceCard({ provenance, version }: { provenance: Provenance; version?: string }) {
  return <section className="mb-5 rounded-lg border border-primary/25 bg-primary/5 p-4" aria-label="Provenance model AI">
    <div className="mb-3 flex items-start justify-between gap-3">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-white"><BrainCircuit size={18} /></span>
        <div><h3 className="text-sm font-semibold text-primary">Model AI Aktif</h3><p className="mono text-[9px] text-muted">{version ?? "historical-model"}</p></div>
      </div>
      <span className="rounded bg-primary px-2 py-1 text-[9px] font-semibold uppercase text-white">Data Training Nyata</span>
    </div>
    <dl className="space-y-2 text-xs">
      <div className="flex gap-2"><Database className="mt-0.5 shrink-0 text-primary" size={14} /><div><dt className="font-semibold">{provenance.algorithm}</dt><dd className="text-muted">Dilatih dari {provenance.trainingEvents} kejadian banjir di {provenance.trainingRegions} region Indonesia ? {provenance.source}</dd></div></div>
      <div className="flex gap-2"><MapPinned className="mt-0.5 shrink-0 text-primary" size={14} /><div><dt className="font-semibold">Probabilitas per koridor OSM</dt><dd className="text-muted">{provenance.probabilitySemantics}.</dd></div></div>
    </dl>
    <div className="mt-3 border-t border-primary/15 pt-3 text-[10px] leading-relaxed text-muted">
      <strong className="text-ink">Batas klaim:</strong> Jakarta adalah pilot inferensi dan belum menjadi region validasi berlabel. Geometri replay Maret 2025 bersifat perkiraan; data bisnis tetap simulasi.
    </div>
  </section>;
}
