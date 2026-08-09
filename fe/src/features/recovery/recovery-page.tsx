"use client";

import { ArrowDown, ArrowRight, CheckCircle2, Factory, Info, Route, ShoppingBag, Truck, Waves } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { SimulationDetails } from "@/components/simulation/simulation-details";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { CommerceAction, LogisticsAction, ManufacturingAction } from "@/domain/recovery";
import { useRecoveryPlan, useSimulation } from "@/hooks/use-resilichain-data";
import { formatMinutes, formatRisk } from "@/lib/format";

function Reasoning({ action }: { action: { what: string; why: string; expectedImpact: string } }) {
  return <div className="space-y-4 border-t border-outline/40 pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"><div><div className="eyebrow mb-1">What</div><p className="text-sm">{action.what}</p></div><div><div className="eyebrow mb-1">Why</div><p className="text-sm leading-snug text-muted">{action.why}</p></div><div><div className="eyebrow mb-1 flex items-center gap-1 text-primary"><CheckCircle2 size={15} /> Projected impact</div><p className="font-semibold leading-snug">{action.expectedImpact}</p></div></div>;
}

function ManufacturingCard({ actions }: { actions: ManufacturingAction[] }) {
  const explanation = actions[0];
  return <PlanSection icon={Factory} title="Manufacturing Adjustments" accent="bg-primary"><div className="grid gap-6 lg:grid-cols-12"><div className="space-y-2 lg:col-span-5">{actions.map((action, index) => <div key={action.id}><div className={`flex items-center justify-between rounded-md border p-3 ${action.changeQuantity < 0 ? "border-danger/20 bg-danger-soft/20" : "border-primary/20 bg-primary/5"}`}><div><div className="text-sm font-semibold">{action.productName}</div><div className="text-xs text-muted">Baseline: {action.baselineQuantity.toLocaleString()} Â· Recovery: {action.recoveryQuantity.toLocaleString()}</div></div><strong className={action.changeQuantity < 0 ? "text-danger" : "text-primary"}>{action.changeQuantity > 0 ? "+" : ""}{action.changeQuantity} units</strong></div>{index < actions.length - 1 && <ArrowDown className="mx-auto my-1 text-outline" size={17} />}</div>)}</div><div className="lg:col-span-7">{explanation && <Reasoning action={{ what: actions.map((x) => x.what).join(" "), why: explanation.why, expectedImpact: actions.map((x) => x.expectedImpact).join(" ") }} />}</div></div></PlanSection>;
}

function LogisticsCard({ actions }: { actions: LogisticsAction[] }) {
  const action = actions[0]; if (!action) return null;
  return <PlanSection icon={Truck} title="Logistics Rerouting" accent="bg-primary"><div className="grid gap-6 lg:grid-cols-12"><div className="overflow-x-auto lg:col-span-5"><table className="w-full min-w-[430px] text-left text-xs"><thead><tr className="border-b border-outline"><th className="eyebrow pb-2">Order & route</th><th className="eyebrow pb-2 text-right">Action</th></tr></thead><tbody>{actions.map((item) => <tr key={item.id} className="border-b border-outline/30"><td className="py-3"><strong>{item.orderId}: {item.originalWarehouseName} â†’ {item.recoveryWarehouseName}</strong><div className="mt-1 text-danger">Normal route Â· {formatRisk(item.baselineFloodExposure)} risk Â· {formatMinutes(item.baselineEtaMinutes)}</div><div className="text-primary">Recovery route Â· {formatRisk(item.recoveryFloodExposure)} risk Â· {formatMinutes(item.recoveryEtaMinutes)}</div><div className="mono mt-1 text-[10px] text-muted">Vehicle {item.vehicleId}</div></td><td className="py-3 text-right"><span className="rounded bg-primary/10 px-2 py-1 font-semibold uppercase text-primary">{item.action.replaceAll("-", " + ")}</span></td></tr>)}</tbody></table></div><div className="lg:col-span-7"><Reasoning action={action} /></div></div></PlanSection>;
}

function CommerceCard({ actions }: { actions: CommerceAction[] }) {
  const action = actions[0]; if (!action) return null;
  return <PlanSection icon={ShoppingBag} title="Commerce Allocation" accent="bg-slate-600"><div className="grid gap-6 lg:grid-cols-12"><div className="lg:col-span-5">{actions.map((item) => <div key={item.id} className="border-b border-outline/30 pb-3"><div className="flex items-start justify-between gap-3"><div><strong className="text-sm">{item.orderId} ({item.storeName})</strong><p className="mt-1 text-xs text-muted">Recommendation: {item.action.replaceAll("-", " + ")}</p></div><div className="text-right text-sm font-semibold text-primary">{item.allocations.map((allocation) => <div key={allocation.productName}>{allocation.quantity} {allocation.productName}</div>)}</div></div></div>)}</div><div className="lg:col-span-7"><Reasoning action={action} /></div></div></PlanSection>;
}

function PlanSection({ icon: Icon, title, accent, children }: { icon: typeof Factory; title: string; accent: string; children: React.ReactNode }) {
  return <section className="relative mb-8 pl-8 before:absolute before:bottom-[-32px] before:left-[11px] before:top-6 before:w-0.5 before:bg-outline last:before:hidden"><span className={`absolute left-[6px] top-5 h-3 w-3 rounded-full border-2 border-white ${accent}`} /><div className="mb-3 flex items-center gap-2"><Icon size={20} className="text-primary" /><h2 className="section-title">{title}</h2></div><div className="card p-4">{children}</div></section>;
}

export function RecoveryPage() {
  const simulationId = useSearchParams().get("simulation") ?? ""; const plan = useRecoveryPlan(simulationId); const simulation = useSimulation(simulationId); const [details, setDetails] = useState(false);
  return <AppShell title="AI Recovery Plan" actions={<button onClick={() => setDetails(true)} className="hidden items-center gap-2 rounded-lg border border-outline px-3 py-2 text-xs font-semibold hover:bg-surface-low sm:flex"><Info size={16} /> Simulation Details</button>}>
    <div className="p-4 md:p-8"><div className="mx-auto max-w-5xl">
      {!simulationId && <EmptyState title="No simulation selected" message="Generate a recovery plan from a disruption analysis first." />}
      {simulationId && plan.isLoading && <LoadingState label="Loading coordinated recovery planâ€¦" />}
      {plan.isError && <ErrorState message={plan.error.message} onRetry={() => void plan.refetch()} />}
      {(plan.data?.status === "queued" || plan.data?.status === "processing") && <LoadingState label="Generating coordinated recovery plan…" />}
      {plan.data?.status === "failed" && <ErrorState message={plan.data.error.message} onRetry={() => void plan.refetch()} />}
      {plan.data?.status === "no-feasible-plan" && <div className="card border-danger/30 p-6"><Waves className="mb-3 text-danger" /><h1 className="section-title text-danger">No Fully Feasible Recovery Plan</h1><p className="mt-2 text-sm text-muted">Recoverable orders: {plan.data.summary.recoverableOrders} / {plan.data.summary.totalOrders}</p><ul className="mt-4 list-disc pl-5 text-sm text-muted">{plan.data.possibleNextActions.map((item) => <li key={item}>{item}</li>)}</ul></div>}
      {plan.data && (plan.data.status === "ready" || plan.data.status === "partial") && <><div className="mb-8"><div className="eyebrow mb-3">Overall Recovery Summary</div><div className="card grid grid-cols-2 gap-4 p-5 lg:grid-cols-4">{[["Status", plan.data.status === "partial" ? "Recommended Â· Partial" : "Plan Ready", CheckCircle2], ["Risks Mitigated", plan.data.summary.risksMitigated, Waves], ["Operational Changes", plan.data.summary.operationalChanges, Route], ["Order Recovery", `${plan.data.summary.recoverableOrders}/${plan.data.summary.totalOrders}`, ShoppingBag]].map(([label, value, Icon]) => { const I = Icon as typeof CheckCircle2; return <div key={String(label)} className="border-r-0 border-outline lg:border-r last:border-r-0"><div className="eyebrow mb-1">{String(label)}</div><div className="flex items-center gap-2 text-xl font-semibold text-primary"><I size={20} />{String(value)}</div></div>; })}</div></div>
        <div><ManufacturingCard actions={plan.data.manufacturingActions} /><LogisticsCard actions={plan.data.logisticsActions} /><CommerceCard actions={plan.data.commerceActions} /></div>
        <div className="flex justify-end"><Link href={`/impact?simulation=${simulationId}`} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-dark">Compare with Baseline <ArrowRight size={17} /></Link></div></>}
    </div></div>{simulation.data && <SimulationDetails simulation={simulation.data} open={details} onClose={() => setDetails(false)} />}
  </AppShell>;
}
