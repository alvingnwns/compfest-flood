"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Simulation } from "@/domain/scenario";

export function SimulationDetails({ simulation, open, onClose }: { simulation: Simulation; open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = ref.current; if (!dialog) return; if (open && !dialog.open) dialog.showModal(); if (!open && dialog.open) dialog.close(); }, [open]);
  const rows = [
    ["Scenario ID", simulation.scenarioId], ["Scenario Mode", "Historical Replay"], ["Model Version", simulation.modelVersion ?? "Pending"],
    ["Optimizer Version", simulation.optimizerVersion ?? "Pending"], ["Simulation Timestamp", new Date(simulation.createdAt).toLocaleString("en-GB")],
    ["Data Mode", simulation.dataMode], ["Historical Data", simulation.historicalDataStatus],
  ];
  return <dialog ref={ref} onClose={onClose} className="m-auto w-[min(92vw,560px)] rounded-xl border border-outline bg-surface p-0 text-ink shadow-2xl backdrop:bg-slate-950/30">
    <div className="flex items-center justify-between border-b border-outline px-5 py-4"><div><h2 className="text-lg font-semibold">Simulation Details</h2><p className="text-xs text-muted">Decision support metadata</p></div><button aria-label="Close simulation details" onClick={onClose} className="rounded-md p-2 hover:bg-surface-high"><X size={18} /></button></div>
    <dl className="divide-y divide-outline/50 px-5">{rows.map(([label, value]) => <div key={label} className="grid grid-cols-[150px_1fr] gap-4 py-3 text-sm"><dt className="text-muted">{label}</dt><dd className="mono break-all text-xs font-medium">{value}</dd></div>)}</dl>
    <div className="m-5 rounded-lg border border-primary/20 bg-primary-soft p-3 text-xs text-primary"><strong>Decision Support Only.</strong> The operator remains the final decision maker.</div>
  </dialog>;
}
