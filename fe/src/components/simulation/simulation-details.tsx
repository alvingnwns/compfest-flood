"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Simulation } from "@/domain/scenario";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { formatDataMode, formatHistoricalStatus } from "@/lib/format";

export function SimulationDetails({ simulation, open, onClose }: { simulation: Simulation; open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; if (!dialog) return; if (open && !dialog.open) dialog.showModal(); if (!open && dialog.open) dialog.close(); }, [open]);
  const dynamic = simulation.analysisMode === "scenario-simulation" && simulation.hazard !== undefined;
  const rows = [
    ["ID Skenario", simulation.scenarioId], ["Mode Analisis", dynamic ? "Simulasi Kondisi" : "Pemutaran Ulang Historis"],
    ...(dynamic ? [["Pola Curah Hujan", getRainfallScenario(simulation.hazard?.rainfallScenario)?.label ?? "Tidak tersedia"], ["Indeks Hazard Relatif", simulation.hazard?.relativeHazardIndex.toFixed(2) ?? "Tidak tersedia"]] : []),
    ["Versi Model", simulation.modelVersion ?? "Menunggu"],
    ["Versi Pengoptimal", simulation.optimizerVersion ?? "Menunggu"], ["Waktu Simulasi", new Date(simulation.createdAt).toLocaleString("id-ID")],
    ["Business Data", simulation.businessDataSource === "custom" ? "Custom Upload" : "Demo"],
    ["Mode Data", formatDataMode(simulation.dataMode)], ["Data Historis", formatHistoricalStatus(simulation.historicalDataStatus)],
  ];
  return <dialog ref={ref} onClose={onClose} className="m-auto w-[min(92vw,560px)] rounded-xl border border-outline bg-surface p-0 text-ink shadow-2xl backdrop:bg-slate-950/30">
    <div className="flex items-center justify-between border-b border-outline px-5 py-4"><div><h2 className="text-lg font-semibold">Detail Simulasi</h2><p className="text-xs text-muted">Metadata pendukung keputusan</p></div><button aria-label="Tutup detail simulasi" onClick={onClose} className="rounded-md p-2 hover:bg-surface-high"><X size={18} /></button></div>
    <dl className="divide-y divide-outline/50 px-5">{rows.map(([label, value]) => <div key={label} className="grid grid-cols-[150px_1fr] gap-4 py-3 text-sm"><dt className="text-muted">{label}</dt><dd className="mono break-all text-xs font-medium">{value}</dd></div>)}</dl>
    <div className="m-5 rounded-lg border border-primary/20 bg-primary-soft p-3 text-xs text-primary"><strong>Hanya Pendukung Keputusan.</strong> Operator tetap menjadi pengambil keputusan akhir.</div>
  </dialog>;
}
