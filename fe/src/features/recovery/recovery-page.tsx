"use client";

import { ArrowRight, CheckCircle2, Factory, Info, Route, ShoppingBag, Truck, Waves } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { SimulationDetails } from "@/components/simulation/simulation-details";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { CommerceAction, LogisticsAction, ManufacturingAction } from "@/domain/recovery";
import { useRecoveryPlan, useSimulation } from "@/hooks/use-resilichain-data";
import { formatAction, formatMinutes, formatRisk } from "@/lib/format";

function Reasoning({ action }: { action: { what: string; why: string; expectedImpact: string } }) {
  return (
    <div className="mt-5 border-t border-outline/40 pt-5">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-outline/40 bg-surface-low p-4">
          <div className="eyebrow mb-1 text-muted">Apa</div>
          <p className="text-sm font-medium text-ink">{action.what}</p>
        </div>
        <div className="rounded-lg border border-outline/40 bg-surface-low p-4">
          <div className="eyebrow mb-1 text-muted">Alasan</div>
          <p className="text-sm leading-snug text-muted">{action.why}</p>
        </div>
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
          <div className="eyebrow mb-1 flex items-center gap-1 text-primary">
            <CheckCircle2 size={15} /> Proyeksi Dampak
          </div>
          <p className="text-sm font-semibold leading-snug text-primary">{action.expectedImpact}</p>
        </div>
      </div>
    </div>
  );
}

function ManufacturingCard({ actions }: { actions: ManufacturingAction[] }) {
  const explanation = actions[0];
  return (
    <PlanSection icon={Factory} title="Penyesuaian Produksi" accent="bg-primary">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map((action) => (
            <div
              key={action.id}
              className={`flex items-center justify-between rounded-lg border p-4 ${
                action.changeQuantity < 0
                  ? "border-danger/20 bg-danger-soft/20"
                  : "border-primary/20 bg-primary/5"
              }`}
            >
              <div>
                <div className="text-sm font-semibold text-ink">{action.productName}</div>
                <div className="text-xs text-muted">
                  Kondisi awal: {action.baselineQuantity.toLocaleString()} · Pemulihan: {action.recoveryQuantity.toLocaleString()}
                </div>
              </div>
              <strong className={`text-sm ${action.changeQuantity < 0 ? "text-danger" : "text-primary"}`}>
                {action.changeQuantity > 0 ? "+" : ""}
                {action.changeQuantity} unit
              </strong>
            </div>
          ))}
        </div>
        {explanation && (
          <Reasoning
            action={{
              what: actions.map((x) => x.what).join(" "),
              why: explanation.why,
              expectedImpact: actions.map((x) => x.expectedImpact).join(" "),
            }}
          />
        )}
      </div>
    </PlanSection>
  );
}

function LogisticsCard({ actions }: { actions: LogisticsAction[] }) {
  const action = actions[0];
  if (!action) return null;
  return (
    <PlanSection icon={Truck} title="Pengalihan Rute Logistik" accent="bg-primary">
      <div className="space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-outline">
                <th className="eyebrow pb-2">Pesanan & Rute</th>
                <th className="eyebrow pb-2">Rute Normal</th>
                <th className="eyebrow pb-2">Rute Pemulihan</th>
                <th className="eyebrow pb-2">Kendaraan</th>
                <th className="eyebrow pb-2 text-right">Tindakan</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((item) => (
                <tr key={item.id} className="border-b border-outline/30 last:border-b-0">
                  <td className="py-3 pr-4">
                    <strong className="text-sm text-ink">
                      {item.orderId}: {item.originalWarehouseName} → {item.recoveryWarehouseName}
                    </strong>
                  </td>
                  <td className="py-3 pr-4 text-danger">
                    <div>{formatRisk(item.baselineFloodExposure)} risiko</div>
                    <div className="mono text-[11px]">{formatMinutes(item.baselineEtaMinutes)}</div>
                  </td>
                  <td className="py-3 pr-4 font-medium text-primary">
                    <div>{formatRisk(item.recoveryFloodExposure)} risiko</div>
                    <div className="mono text-[11px]">{formatMinutes(item.recoveryEtaMinutes)}</div>
                  </td>
                  <td className="py-3 pr-4 mono text-muted">
                    {item.vehicleId}
                  </td>
                  <td className="py-3 text-right align-middle">
                    <span className="inline-block rounded bg-primary/10 px-2.5 py-1 font-semibold uppercase text-primary text-[11px]">
                      {formatAction(item.action)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Reasoning action={action} />
      </div>
    </PlanSection>
  );
}

function CommerceCard({ actions }: { actions: CommerceAction[] }) {
  const action = actions[0];
  if (!action) return null;
  return (
    <PlanSection icon={ShoppingBag} title="Alokasi Perdagangan" accent="bg-slate-600">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map((item) => (
            <div key={item.id} className="rounded-lg border border-outline/40 bg-surface-low p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <strong className="text-sm text-ink">
                    {item.orderId} ({item.storeName})
                  </strong>
                  <p className="mt-1 text-xs text-muted">Rekomendasi: {formatAction(item.action)}</p>
                </div>
                <div className="text-right text-xs font-semibold text-primary">
                  {item.allocations.map((allocation) => (
                    <div key={allocation.productName}>
                      {allocation.quantity} {allocation.productName}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        <Reasoning action={action} />
      </div>
    </PlanSection>
  );
}

function PlanSection({
  icon: Icon,
  title,
  accent,
  children,
}: {
  icon: typeof Factory;
  title: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <section className="relative mb-8 pl-8 before:absolute before:bottom-[-32px] before:left-[11px] before:top-6 before:w-0.5 before:bg-outline last:before:hidden">
      <span className={`absolute left-[6px] top-5 h-3 w-3 rounded-full border-2 border-white ${accent}`} />
      <div className="mb-3 flex items-center gap-2">
        <Icon size={20} className="text-primary" />
        <h2 className="section-title text-ink">{title}</h2>
      </div>
      <div className="card p-5">{children}</div>
    </section>
  );
}

export function RecoveryPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("simulation") ?? "";
  const plan = useRecoveryPlan(simulationId);
  const simulation = useSimulation(simulationId);
  const [details, setDetails] = useState(false);

  return (
    <AppShell
      title="Rencana Pemulihan AI"
      actions={
        <button
          onClick={() => setDetails(true)}
          className="hidden items-center gap-2 rounded-lg border border-outline px-3 py-2 text-xs font-semibold hover:bg-surface-low sm:flex"
        >
          <Info size={16} /> Detail Simulasi
        </button>
      }
    >
      <div className="p-4 md:p-8">
        <div className="w-full">
          {!simulationId && (
            <EmptyState
              title="Belum ada simulasi yang dipilih"
              message="Buat rencana pemulihan dari analisis gangguan terlebih dahulu."
            />
          )}
          {simulationId && plan.isLoading && <LoadingState label="Memuat rencana pemulihan terkoordinasi…" />}
          {plan.isError && <ErrorState message={plan.error.message} onRetry={() => void plan.refetch()} />}
          {(plan.data?.status === "queued" || plan.data?.status === "processing") && (
            <LoadingState label="Menyusun rencana pemulihan terkoordinasi…" />
          )}
          {plan.data?.status === "failed" && (
            <ErrorState message={plan.data.error.message} onRetry={() => void plan.refetch()} />
          )}
          {plan.data?.status === "no-feasible-plan" && (
            <div className="card border-danger/30 p-6">
              <Waves className="mb-3 text-danger" />
              <h1 className="section-title text-danger">Tidak Ada Rencana Pemulihan yang Sepenuhnya Layak</h1>
              <p className="mt-2 text-sm text-muted">
                Pesanan yang dapat dipulihkan: {plan.data.summary.recoverableOrders} / {plan.data.summary.totalOrders}
              </p>
              <ul className="mt-4 list-disc pl-5 text-sm text-muted">
                {plan.data.possibleNextActions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {plan.data && (plan.data.status === "ready" || plan.data.status === "partial") && (
            <>
              {/* Summary KPIs bar */}
              <div className="mb-8">
                <div className="eyebrow mb-3">Ringkasan Pemulihan Keseluruhan</div>
                <div className="card grid grid-cols-2 gap-4 p-5 lg:grid-cols-4">
                  {[
                    [
                      "Status",
                      plan.data.status === "partial" ? "Direkomendasikan · Sebagian" : "Rencana Siap",
                      CheckCircle2,
                    ],
                    ["Risiko Ditangani", plan.data.summary.risksMitigated, Waves],
                    ["Perubahan Operasional", plan.data.summary.operationalChanges, Route],
                    [
                      "Pemulihan Pesanan",
                      `${plan.data.summary.recoverableOrders}/${plan.data.summary.totalOrders}`,
                      ShoppingBag,
                    ],
                  ].map(([label, value, Icon]) => {
                    const I = Icon as typeof CheckCircle2;
                    return (
                      <div key={String(label)} className="border-r-0 border-outline last:border-r-0 lg:border-r">
                        <div className="eyebrow mb-1">{String(label)}</div>
                        <div className="flex items-center gap-2 text-xl font-semibold text-primary">
                          <I size={20} />
                          {String(value)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Action sections */}
              <div>
                <ManufacturingCard actions={plan.data.manufacturingActions} />
                <LogisticsCard actions={plan.data.logisticsActions} />
                <CommerceCard actions={plan.data.commerceActions} />
              </div>

              {/* Navigation button */}
              <div className="flex justify-end pt-4">
                <Link
                  href={`/impact?simulation=${simulationId}`}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-primary-dark"
                >
                  Bandingkan dengan Kondisi Awal <ArrowRight size={17} />
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
      {simulation.data && (
        <SimulationDetails simulation={simulation.data} open={details} onClose={() => setDetails(false)} />
      )}
    </AppShell>
  );
}
