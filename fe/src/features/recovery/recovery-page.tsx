"use client";

import {
  ArrowRight,
  BadgeCheck,
  CloudRain,
  Factory,
  MapPin,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import type { CommerceAction, LogisticsAction, ManufacturingAction } from "@/domain/recovery";
import type { Simulation } from "@/domain/scenario";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useRecoveryPlan, useSimulation } from "@/hooks/use-aruna-data";
import { formatAction, formatMinutes } from "@/lib/format";

type RecoveryView = "production" | "routes" | "commerce";

const recoveryViews: Array<{ id: RecoveryView; label: string }> = [
  { id: "production", label: "Penyesuaian Produksi" },
  { id: "routes", label: "Pengalihan Rute" },
  { id: "commerce", label: "Alokasi Perdagangan" },
];

function RecoveryContext({
  simulation,
  operationalCondition,
}: {
  simulation: Simulation;
  operationalCondition: string;
}) {
  const rainfall =
    simulation.analysisMode === "scenario-simulation"
      ? getRainfallScenario(simulation.hazard?.rainfallScenario)?.label
      : "04 Mar 2025";
  const simulationLabel =
    simulation.analysisMode === "scenario-simulation" ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta";

  return (
    <section className="overflow-hidden rounded-[22px] bg-white shadow-[0_0_15px_rgb(0_0_0/18%)]" aria-label="Konteks rencana pemulihan">
      <div className="flex h-[58px] items-center justify-center bg-primary px-5 text-center text-[19px] font-bold text-white">
        Rencana Pemulihan
      </div>
      <div className="grid grid-cols-2 gap-5 px-7 py-5 text-[12px]">
        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wide text-[#979797]">
            <span>KONDISI LINGKUNGAN</span>
            <CloudRain className="size-[18px] shrink-0 text-primary" />
          </div>
          <div className="text-[14px] font-bold text-black">{rainfall ?? "Pola Hujan"}</div>
          <div className="mt-1 text-[12px] leading-tight text-[#5a5a5a]">{simulationLabel}</div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] font-bold uppercase tracking-wide text-[#979797]">
            <span>KONDISI OPERASIONAL</span>
            <Factory className="size-[18px] shrink-0 text-primary" />
          </div>
          <div className="text-[14px] font-bold text-black">{operationalConditionLabel(operationalCondition)}</div>
          <div className="mt-1 flex items-center gap-1.5 text-[12px] text-[#5a5a5a]"><MapPin className="size-3.5 shrink-0 text-primary" /> Jakarta</div>
        </div>
      </div>
    </section>
  );
}

function RecoveryTabs({
  active,
  onChange,
}: {
  active: RecoveryView;
  onChange: (view: RecoveryView) => void;
}) {
  return (
    <div className="mt-6 rounded-[22px] border-[6px] border-primary bg-primary p-0.5" role="tablist" aria-label="Bagian rencana pemulihan">
      {recoveryViews.map((view) => (
        <button
          key={view.id}
          type="button"
          role="tab"
          aria-selected={active === view.id}
          onClick={() => onChange(view.id)}
          className={`mb-1 flex h-[57px] w-full items-center justify-center rounded-[14px] px-4 text-[16px] font-bold transition duration-200 last:mb-0 ${active === view.id ? "bg-[#eba92d] text-white shadow-sm" : "bg-[#fff1dd] text-primary hover:bg-[#ffe5bd]"}`}
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}

function RecoverySummary({
  status,
  risks,
  changes,
  recoverable,
  total,
}: {
  status: "ready" | "partial";
  risks: number;
  changes: number;
  recoverable: number;
  total: number;
}) {
  const metrics = [
    {
      label: "STATUS",
      value: status === "partial" ? "Rencana Parsial" : "Rencana Siap",
      icon: true,
    },
    { label: "RISIKO\nDITANGANI", value: String(risks) },
    { label: "PERUBAHAN\nOPERASIONAL", value: String(changes) },
    { label: "PEMULIHAN\nPESANAN", value: `${recoverable}/${total}` },
  ];

  return (
    <section className="shrink-0 overflow-hidden rounded-t-[58px] bg-white shadow-[0_0_8px_rgb(0_0_0/20%)]" aria-label="Ringkasan rencana pemulihan">
      <div className="bg-primary px-6 py-[25px] text-center text-[24px] font-semibold tracking-[3px] text-white">
        RINGKASAN RENCANA PEMULIHAN
      </div>
      <div className="grid min-h-[140px] grid-cols-2 divide-x divide-primary/80 px-4 py-4 md:grid-cols-4">
        {metrics.map((metric) => (
          <div key={metric.label} className="flex min-w-0 flex-col items-center justify-center px-3 text-center">
            <div className="whitespace-pre-line text-[14px] font-semibold leading-tight tracking-[2px] text-[#5a5a5a]">{metric.label}</div>
            {metric.icon ? (
              <>
                <BadgeCheck className="mt-2 h-12 w-12 text-[#00b98e]" strokeWidth={2.5} />
                <div className="text-[13px] font-semibold text-[#00b98e]">{metric.value}</div>
              </>
            ) : (
              <div className="mt-2 text-[42px] font-semibold leading-none text-[#00b98e]">{metric.value}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function ReasoningCards({ action }: { action?: { what: string; why: string; expectedImpact: string } }) {
  if (!action) return null;
  const cards = [
    ["SARAN", action.what],
    ["ALASAN", action.why],
    ["DAMPAK", action.expectedImpact],
  ];
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {cards.map(([label, value]) => (
        <div key={label} className="min-h-[150px] rounded-[20px] border border-[#b3b3b3] bg-gradient-to-b from-[#ededed] to-[#c4c4c4] px-5 py-4 text-[#323232]">
          <div className="mb-2 text-center text-[15px] font-bold tracking-[2px] text-[#5a5a5a]">{label}</div>
          <p className="text-[12px] leading-snug">{value}</p>
        </div>
      ))}
    </div>
  );
}

function ProductionView({ actions }: { actions: ManufacturingAction[] }) {
  if (actions.length === 0) {
    return (
      <div>
        <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">PENYESUAIAN PRODUKSI</h2>
        <div className="rounded-[42px] bg-white p-8 shadow-sm text-center">
          <div className="mx-auto max-w-md py-4">
            <p className="text-[17px] font-bold text-primary">Jadwal Produksi Optimal Terjaga</p>
            <p className="mt-2 text-[13px] leading-relaxed text-[#5a5a5a]">
              Tidak diperlukan perubahan kuantitas produksi pabrik. Alokasi produksi saat ini telah optimal untuk mendukung pemenuhan pesanan dan pengalihan rute logistik.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">PENYESUAIAN PRODUKSI</h2>
      <div className="rounded-[42px] bg-white p-6 shadow-sm">
        <div className="mb-4 grid gap-4 md:grid-cols-2">
          {actions.map((action) => {
            const negative = action.changeQuantity < 0;
            return (
              <article
                key={action.id}
                className={`flex min-h-[150px] items-center justify-between gap-4 rounded-[20px] border px-7 py-5 ${negative
                    ? "border-[#bc0000] bg-[#f3cfcf] text-[#5a0000]"
                    : "border-[#84b7ab] bg-[#d5eee8] text-[#005a45]"
                  }`}
              >
                <div>
                  <h3 className="mb-3 text-[21px] font-bold">{action.productName}</h3>
                  <div className="flex gap-2 text-center text-white">
                    <div className={`rounded-[10px] px-3 py-2 ${negative ? "bg-[#b75152]" : "bg-[#00b98e]"}`}>
                      <div className="text-[10px] opacity-70">Sebelum</div>
                      <strong className="text-[17px]">{action.baselineQuantity}</strong>
                    </div>
                    <div className={`rounded-[10px] px-3 py-2 ${negative ? "bg-[#721516]" : "bg-[#00a82d]"}`}>
                      <div className="text-[10px] opacity-70">Setelah</div>
                      <strong className="text-[17px]">{action.recoveryQuantity}</strong>
                    </div>
                  </div>
                </div>
                <div className="text-center">
                  <strong className="block text-[48px] leading-none">
                    {action.changeQuantity > 0 ? `+${action.changeQuantity}` : action.changeQuantity}
                  </strong>
                  <span className="text-[21px] font-bold">Unit</span>
                </div>
              </article>
            );
          })}
        </div>
        <ReasoningCards action={actions[0]} />
      </div>
    </div>
  );
}

function RoutesView({ actions }: { actions: LogisticsAction[] }) {
  return (
    <div>
      <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">PENGALIHAN RUTE LOGISTIK</h2>
      <div className="overflow-hidden rounded-[42px] bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="bg-primary text-[12px] font-semibold text-white">
              <tr>
                <th className="px-5 py-5 text-center">ID</th>
                <th className="px-4 py-5 text-center">PESANAN &amp;<br />RUTE</th>
                <th className="px-4 py-5 text-center">RUTE<br />NORMAL</th>
                <th className="px-4 py-5 text-center">RUTE<br />PEMULIHAN</th>
                <th className="px-4 py-5 text-center">KENDARAAN</th>
                <th className="px-4 py-5 text-center">TRANSAKSI</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((action, index) => (
                <tr key={action.id} className="border-b border-[#b3b3b3] last:border-b-0">
                  <td className="px-5 py-4 text-center text-[23px] font-bold">{String(index + 1).padStart(2, "0")}</td>
                  <td className="px-4 py-4 text-[14px] font-medium">{action.originalWarehouseName} -<br />{action.recoveryWarehouseName}</td>
                  <td className="px-4 py-4 text-center text-[18px]">{formatMinutes(action.baselineEtaMinutes)}</td>
                  <td className="px-4 py-4 text-center text-[18px]">{formatMinutes(action.recoveryEtaMinutes)}</td>
                  <td className="px-4 py-4 text-center text-[14px]">{action.vehicleId}</td>
                  <td className="px-4 py-4 text-center">
                    <span className="inline-block rounded-full bg-[#a9eadb] px-3.5 py-1 text-[12px] font-semibold text-[#006c53]">{formatAction(action.action)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CommerceView({ actions }: { actions: CommerceAction[] }) {
  return (
    <div>
      <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">ALOKASI PERDAGANGAN</h2>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {actions.map((action) => (
          <article key={action.id} className="min-h-[154px] rounded-[34px] bg-white px-7 py-6 shadow-sm">
            <h3 className="mb-3 text-[24px] font-bold text-black">{action.orderId}</h3>
            <p className="text-[14px] text-[#5a5a5a]">Rekomendasi: {formatAction(action.action)}</p>
            {action.allocations.map((allocation) => (
              <p key={allocation.productId} className="text-[14px] text-[#5a5a5a]">{allocation.quantity} {allocation.productName}</p>
            ))}
          </article>
        ))}
      </div>
    </div>
  );
}

export function RecoveryPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("simulation") ?? "";
  const operationalCondition = searchParams.get("condition") ?? "normal";
  const plan = useRecoveryPlan(simulationId);
  const simulation = useSimulation(simulationId);
  const [activeView, setActiveView] = useState<RecoveryView>("production");

  const readyPlan = plan.data && (plan.data.status === "ready" || plan.data.status === "partial") ? plan.data : undefined;

  return (
    <AppShell title="Rencana Pemulihan">
      <div className="impact-pattern min-h-[calc(100vh-80px)] p-4 md:min-h-[calc(100vh-80px)] md:p-6 xl:h-[calc(100vh-80px)] xl:overflow-hidden xl:px-8 xl:py-6">
        {!simulationId && (
          <EmptyState title="Belum ada simulasi yang dipilih" message="Buat rencana pemulihan dari analisis gangguan terlebih dahulu." />
        )}
        {simulationId && (plan.isLoading || simulation.isLoading) && <LoadingState label="Memuat rencana pemulihan terkoordinasi..." />}
        {plan.isError && <ErrorState message={plan.error.message} onRetry={() => void plan.refetch()} />}
        {(plan.data?.status === "queued" || plan.data?.status === "processing") && <LoadingState label="Menyusun rencana pemulihan terkoordinasi..." />}
        {plan.data?.status === "failed" && <ErrorState message={plan.data.error.message} onRetry={() => void plan.refetch()} />}
        {plan.data?.status === "no-feasible-plan" && (
          <div className="rounded-[24px] border border-danger/30 bg-white p-6 shadow-sm">
            <h1 className="text-xl font-bold text-danger">Tidak Ada Rencana Pemulihan yang Sepenuhnya Layak</h1>
            <p className="mt-2 text-sm text-muted">Pesanan yang dapat dipulihkan: {plan.data.summary.recoverableOrders} / {plan.data.summary.totalOrders}</p>
          </div>
        )}
        {simulation.data && readyPlan && (
          <div className="mx-auto grid max-w-[1480px] gap-7 xl:h-full xl:grid-cols-[325px_minmax(0,1fr)] xl:gap-[36px]">
            <aside className="xl:min-h-0">
              <RecoveryContext simulation={simulation.data} operationalCondition={operationalCondition} />
              <RecoveryTabs active={activeView} onChange={setActiveView} />
            </aside>
            <section className="flex min-w-0 flex-col overflow-hidden rounded-t-[58px] bg-[#dce9f3]/80 shadow-[0_0_15px_rgb(0_0_0/18%)] xl:min-h-0">
              <RecoverySummary
                status={readyPlan.status === "partial" ? "partial" : "ready"}
                risks={readyPlan.summary.risksMitigated}
                changes={readyPlan.summary.operationalChanges}
                recoverable={readyPlan.summary.recoverableOrders}
                total={readyPlan.summary.totalOrders}
              />
              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-8 md:px-12">
                {activeView === "production" && <ProductionView actions={readyPlan.manufacturingActions} />}
                {activeView === "routes" && <RoutesView actions={readyPlan.logisticsActions} />}
                {activeView === "commerce" && <CommerceView actions={readyPlan.commerceActions} />}
                <div className="mt-10 flex justify-center pb-3">
                  {activeView === "production" && (
                    <button
                      type="button"
                      onClick={() => setActiveView("routes")}
                      className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]"
                    >
                      <span>LIHAT PENGALIHAN RUTE LOGISTIK</span>
                      <ArrowRight size={26} strokeWidth={2.5} />
                    </button>
                  )}
                  {activeView === "routes" && (
                    <button
                      type="button"
                      onClick={() => setActiveView("commerce")}
                      className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]"
                    >
                      <span>LIHAT ALOKASI PERDAGANGAN</span>
                      <ArrowRight size={26} strokeWidth={2.5} />
                    </button>
                  )}
                  {activeView === "commerce" && (
                    <Link
                      href={`/impact?simulation=${simulationId}&condition=${encodeURIComponent(operationalCondition)}`}
                      className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]"
                    >
                      <RotateCcw size={28} strokeWidth={2.5} />
                      <span>BANDINGKAN DENGAN KONDISI AWAL</span>
                    </Link>
                  )}
                </div>
              </div>
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
