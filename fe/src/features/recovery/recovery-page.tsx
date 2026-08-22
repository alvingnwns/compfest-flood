"use client";

import { ArrowRight, BadgeCheck, CloudRain, Factory, MapPin, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState, ErrorState, FullPageState, LoadingState } from "@/components/ui/states";
import type { CommerceAction, LogisticsAction, ManufacturingAction, ManufacturingPlanExplanation } from "@/domain/recovery";
import type { Simulation } from "@/domain/scenario";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useRecoveryPlan, useSimulation } from "@/hooks/use-aruna-data";
import { formatMinutes } from "@/lib/format";

type RecoveryView = "production" | "routes" | "commerce";

const recoveryViews: Array<{ id: RecoveryView; label: string }> = [
  { id: "production", label: "Penyesuaian Produksi" },
  { id: "routes", label: "Pengalihan Rute" },
  { id: "commerce", label: "Alokasi Pesanan" },
];

function RecoveryContext({ simulation, operationalCondition }: { simulation: Simulation; operationalCondition: string }) {
  const rainfall = simulation.analysisMode === "scenario-simulation" ? getRainfallScenario(simulation.hazard?.rainfallScenario)?.label : "04 Mar 2025";
  const simulationLabel = simulation.analysisMode === "scenario-simulation" ? "Simulasi Kondisi" : "Simulasi Banjir Jakarta";

  return (
    <section className="overflow-hidden rounded-[22px] bg-white shadow-[0_0_15px_rgb(0_0_0/18%)]" aria-label="Konteks rencana pemulihan">
      <div className="flex h-[58px] items-center justify-center bg-primary px-5 text-center text-[19px] font-bold text-white">Rencana Pemulihan</div>
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
          <div className="mt-1 flex items-center gap-1.5 text-[12px] text-[#5a5a5a]">
            <MapPin className="size-3.5 shrink-0 text-primary" /> Jakarta
          </div>
        </div>
      </div>
    </section>
  );
}

function RecoveryTabs({ active, onChange }: { active: RecoveryView; onChange: (view: RecoveryView) => void }) {
  return (
    <div className="mt-6 rounded-[22px] border-[6px] border-primary bg-primary p-0.5" role="tablist" aria-label="Bagian rencana pemulihan">
      {recoveryViews.map((view) => (
        <button key={view.id} type="button" role="tab" aria-selected={active === view.id} onClick={() => onChange(view.id)} className={`mb-1 flex h-[57px] w-full items-center justify-center rounded-[14px] px-4 text-[16px] font-bold transition duration-200 last:mb-0 ${active === view.id ? "bg-[#eba92d] text-white shadow-sm" : "bg-[#fff1dd] text-primary hover:bg-[#ffe5bd]"}`}>
          {view.label}
        </button>
      ))}
    </div>
  );
}

export function RecoverySummary({
  status,
  logisticsAdjustments,
  adjustedProducts,
  recoverable,
  total,
}: {
  status: "ready" | "partial";
  logisticsAdjustments: number;
  adjustedProducts: number;
  recoverable: number;
  total: number;
}) {
  const metrics = [
    {
      label: "STATUS",
      value: status === "partial" ? "Rencana Parsial" : "Rencana Siap",
      icon: true,
    },
    { label: "PENYESUAIAN\nLOGISTIK", value: String(logisticsAdjustments) },
    { label: "PESANAN\nPULIH PENUH", value: `${recoverable}/${total}` },
    { label: "PRODUK\nDISESUAIKAN", value: String(adjustedProducts) },
  ];

  return (
    <section className="shrink-0 overflow-hidden rounded-t-[58px] bg-white shadow-[0_0_8px_rgb(0_0_0/20%)]" aria-label="Ringkasan rencana pemulihan">
      <div className="bg-primary px-6 py-[25px] text-center text-[24px] font-semibold tracking-[3px] text-white">RINGKASAN RENCANA PEMULIHAN</div>
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

function ManufacturingReasoningCards({ actions, explanation }: { actions: ManufacturingAction[]; explanation: ManufacturingPlanExplanation }) {
  const changedActions = actions.filter((action) => action.changeQuantity !== 0);
  const suggestions = changedActions.length > 0 ? changedActions : actions;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="min-h-[150px] rounded-[20px] border border-[#b3b3b3] bg-gradient-to-b from-[#ededed] to-[#c4c4c4] px-5 py-4 text-[#323232]">
        <div className="mb-2 text-center text-[15px] font-bold tracking-[2px] text-[#5a5a5a]">SARAN</div>
        <ul className="space-y-2 text-[12px] leading-snug">
          {suggestions.map((action) => <li key={action.id}>{action.what}</li>)}
        </ul>
      </div>
      <div className="min-h-[150px] rounded-[20px] border border-[#b3b3b3] bg-gradient-to-b from-[#ededed] to-[#c4c4c4] px-5 py-4 text-[#323232]">
        <div className="mb-2 text-center text-[15px] font-bold tracking-[2px] text-[#5a5a5a]">ALASAN</div>
        <p className="text-[12px] leading-snug">{explanation.reason}</p>
      </div>
      <div className="min-h-[150px] rounded-[20px] border border-[#b3b3b3] bg-gradient-to-b from-[#ededed] to-[#c4c4c4] px-5 py-4 text-[#323232]">
        <div className="mb-2 text-center text-[15px] font-bold tracking-[2px] text-[#5a5a5a]">DAMPAK</div>
        <p className="text-[12px] leading-snug">{explanation.expectedImpact}</p>
      </div>
    </div>
  );
}

export function ProductionView({ actions, explanation }: { actions: ManufacturingAction[]; explanation: ManufacturingPlanExplanation }) {
  if (actions.length === 0) {
    return (
      <div>
        <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">PENYESUAIAN PRODUKSI</h2>
        <div className="rounded-[42px] bg-white p-8 shadow-sm text-center">
          <div className="mx-auto max-w-md py-4">
            <p className="text-[17px] font-bold text-primary">Jadwal Produksi Optimal Terjaga</p>
            <p className="mt-2 text-[13px] leading-relaxed text-[#5a5a5a]">Tidak diperlukan perubahan kuantitas produksi pabrik. Alokasi produksi saat ini telah optimal untuk mendukung pemenuhan pesanan dan pengalihan rute logistik.</p>
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
              <article key={action.id} className={`flex min-h-[150px] items-center justify-between gap-4 rounded-[20px] border px-7 py-5 ${negative ? "border-[#bc0000] bg-[#f3cfcf] text-[#5a0000]" : "border-[#84b7ab] bg-[#d5eee8] text-[#005a45]"}`}>
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
                  <strong className="block text-[48px] leading-none">{action.changeQuantity > 0 ? `+${action.changeQuantity}` : action.changeQuantity}</strong>
                  <span className="text-[21px] font-bold">Unit</span>
                </div>
              </article>
            );
          })}
        </div>
        <ManufacturingReasoningCards actions={actions} explanation={explanation} />
      </div>
    </div>
  );
}

const logisticsActionLabels: Record<LogisticsAction["action"], string> = {
  allocate: "Alokasikan pesanan",
  reallocate: "Alihkan gudang",
  reroute: "Ubah rute",
  "reallocate-reroute": "Alihkan + ubah rute",
};

type LogisticsDestination = Pick<CommerceAction, "orderId" | "storeId" | "storeName">;

export function RoutesView({ actions, destinations }: { actions: LogisticsAction[]; destinations: LogisticsDestination[] }) {
  const destinationsByOrderId = new Map(destinations.map((destination) => [destination.orderId, destination]));

  return (
    <div>
      <h2 className="text-center text-[26px] font-bold tracking-[3px] text-primary">PENGALIHAN RUTE LOGISTIK</h2>
      <p className="mx-auto mb-7 mt-2 max-w-[820px] text-center text-[13px] leading-relaxed text-[#5a5a5a]">Setiap baris menunjukkan perubahan cara sebuah pesanan dikirim ke tujuan yang sama, termasuk gudang asal, rute, waktu tempuh, dan kendaraan.</p>
      <div className="overflow-hidden rounded-[42px] bg-white shadow-sm">
        <div className="overflow-hidden">
          <table className="w-full table-fixed border-collapse text-left">
            <colgroup>
              <col className="w-[5%]" />
              <col className="w-[15%]" />
              <col className="w-[14%]" />
              <col className="w-[14%]" />
              <col className="w-[10%]" />
              <col className="w-[10%]" />
              <col className="w-[12%]" />
              <col className="w-[20%]" />
            </colgroup>
            <thead className="bg-primary text-[12px] font-semibold text-white">
              <tr>
                <th className="px-2 py-5 text-center">ID</th>
                <th aria-label="Pesanan / Tujuan" className="px-4 py-5 text-center">
                  PESANAN /<br />
                  TUJUAN
                </th>
                <th aria-label="Gudang Normal" className="px-4 py-5 text-center">
                  GUDANG
                  <br />
                  NORMAL
                </th>
                <th aria-label="Gudang Pemulihan" className="px-4 py-5 text-center">
                  GUDANG
                  <br />
                  PEMULIHAN
                </th>
                <th aria-label="ETA Normal" className="px-4 py-5 text-center">
                  ETA
                  <br />
                  NORMAL
                </th>
                <th aria-label="ETA Pemulihan" className="px-4 py-5 text-center">
                  ETA
                  <br />
                  PEMULIHAN
                </th>
                <th className="px-4 py-5 text-center">KENDARAAN</th>
                <th className="px-3 py-5 text-center">TINDAKAN</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((action, index) => (
                <tr key={action.id} className="border-b border-[#b3b3b3] last:border-b-0">
                  <td className="px-2 py-4 text-center text-[20px] font-bold">{String(index + 1).padStart(2, "0")}</td>
                  <td className="px-4 py-4 text-center">
                    <span className="block text-[14px] font-semibold text-black">{destinationsByOrderId.get(action.orderId)?.storeName ?? "Tujuan tidak tersedia"}</span>
                    <span className="mt-0.5 block text-[11px] font-medium text-[#6b7280]">{action.orderId}</span>
                  </td>
                  <td className="px-4 py-4 text-center text-[14px] font-medium">{action.originalWarehouseName ?? "Belum teralokasi"}</td>
                  <td className="px-4 py-4 text-center text-[14px] font-medium">{action.recoveryWarehouseName}</td>
                  <td className="px-4 py-4 text-center text-[18px]">{action.baselineEtaMinutes == null ? "—" : formatMinutes(action.baselineEtaMinutes)}</td>
                  <td className="px-4 py-4 text-center text-[18px]">{formatMinutes(action.recoveryEtaMinutes)}</td>
                  <td className="px-4 py-4 text-center text-[14px]">{action.vehicleId}</td>
                  <td className="px-3 py-4 text-center">
                    <span className="inline-flex max-w-full items-center justify-center rounded-full bg-[#a9eadb] px-2.5 py-1 text-[12px] font-semibold leading-tight text-[#006c53]">{logisticsActionLabels[action.action]}</span>
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

const commercePriorityLabels: Record<CommerceAction["priority"], string> = {
  normal: "Normal",
  high: "Tinggi",
  critical: "Kritis",
};

export function getCommerceOutcome(action: CommerceAction) {
  const allocatedQuantity = action.allocations.reduce((total, allocation) => total + allocation.quantity, 0);
  const substituteProducts = action.allocations.filter((allocation) => allocation.productId !== action.requestedProductId);
  const hasSubstitute = substituteProducts.length > 0;
  const label = allocatedQuantity === 0
    ? "Tidak dapat dipenuhi"
    : allocatedQuantity < action.requestedQuantity
      ? "Penuhi sebagian"
      : hasSubstitute
        ? "Substitusi"
        : "Penuhi penuh";
  const tone = allocatedQuantity === 0
    ? "bg-[#f3cfcf] text-[#8a1717]"
    : allocatedQuantity < action.requestedQuantity
      ? "bg-[#fff0c9] text-[#7a5200]"
      : "bg-[#a9eadb] text-[#006c53]";

  return { allocatedQuantity, hasSubstitute, label, substituteProducts, tone };
}

export function CommerceView({ actions }: { actions: CommerceAction[] }) {
  return (
    <div>
      <h2 className="mb-7 text-center text-[26px] font-bold tracking-[3px] text-primary">ALOKASI PESANAN</h2>
      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
        {actions.map((action) => {
          const outcome = getCommerceOutcome(action);
          return (
            <article key={action.id} className="min-h-[190px] min-w-0 rounded-[34px] bg-white px-7 py-6 shadow-sm">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                <div className="min-w-0">
                  <h3 className="break-words text-[22px] font-bold leading-tight text-black">{action.orderId}</h3>
                  <p className="mt-1 break-words text-[14px] font-medium text-[#5a5a5a]">{action.storeName}</p>
                </div>
                <span className={`inline-flex max-w-full items-center justify-center whitespace-nowrap rounded-full px-3 py-1 text-[12px] font-semibold leading-tight ${outcome.tone}`}>
                  {outcome.label}
                </span>
              </div>
              <div className="mt-5 border-t border-[#d7d7d7] pt-4">
                <p className="break-words text-[14px] font-semibold text-primary">{action.requestedProductName}</p>
                <p className="mt-1 text-[19px] font-bold text-black">{outcome.allocatedQuantity} / {action.requestedQuantity} unit</p>
                {outcome.hasSubstitute && (
                  <p className="mt-2 break-words text-[12px] text-[#5a5a5a]">
                    Substitusi: {action.requestedProductName} &rarr; {outcome.substituteProducts.map((product) => product.productName).join(" + ")}
                  </p>
                )}
                <p className="mt-2 text-[12px] text-[#6b7280]">Prioritas pesanan: {commercePriorityLabels[action.priority]}</p>
              </div>
            </article>
          );
        })}
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

  if (!simulationId) {
    return (
      <AppShell title="Rencana Pemulihan">
        <FullPageState>
          <EmptyState title="Belum ada simulasi yang dipilih" message="Buat rencana pemulihan dari analisis gangguan terlebih dahulu." />
        </FullPageState>
      </AppShell>
    );
  }

  return (
    <AppShell title="Rencana Pemulihan">
      <div className="impact-pattern min-h-[calc(100vh-80px)] p-4 md:min-h-[calc(100vh-80px)] md:p-6 xl:h-[calc(100vh-80px)] xl:overflow-hidden xl:px-8 xl:py-6">
        {(plan.isLoading || simulation.isLoading) && <LoadingState label="Memuat rencana pemulihan terkoordinasi..." />}
        {plan.isError && <ErrorState message={plan.error.message} onRetry={() => void plan.refetch()} />}
        {(plan.data?.status === "queued" || plan.data?.status === "processing") && <LoadingState label="Menyusun rencana pemulihan terkoordinasi..." />}
        {plan.data?.status === "failed" && <ErrorState message={plan.data.error.message} onRetry={() => void plan.refetch()} />}
        {plan.data?.status === "no-feasible-plan" && (
          <div className="rounded-[24px] border border-danger/30 bg-white p-6 shadow-sm">
            <h1 className="text-xl font-bold text-danger">Tidak Ada Rencana Pemulihan yang Sepenuhnya Layak</h1>
            <p className="mt-2 text-sm text-muted">
              Pesanan yang dapat dipulihkan: {plan.data.summary.recoverableOrders} / {plan.data.summary.totalOrders}
            </p>
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
                logisticsAdjustments={readyPlan.logisticsActions.length}
                adjustedProducts={readyPlan.manufacturingActions.filter((action) => action.changeQuantity !== 0).length}
                recoverable={readyPlan.summary.recoverableOrders}
                total={readyPlan.summary.totalOrders}
              />
              <div className="min-h-0 flex-1 overflow-y-auto px-6 py-8 md:px-12">
                {activeView === "production" && <ProductionView actions={readyPlan.manufacturingActions} explanation={readyPlan.manufacturingExplanation} />}
                {activeView === "routes" && <RoutesView actions={readyPlan.logisticsActions} destinations={readyPlan.commerceActions} />}
                {activeView === "commerce" && <CommerceView actions={readyPlan.commerceActions} />}
                <div className="mt-10 flex justify-center pb-3">
                  {activeView === "production" && (
                    <button type="button" onClick={() => setActiveView("routes")} className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]">
                      <span>LIHAT PENGALIHAN RUTE LOGISTIK</span>
                      <ArrowRight size={26} strokeWidth={2.5} />
                    </button>
                  )}
                  {activeView === "routes" && (
                    <button type="button" onClick={() => setActiveView("commerce")} className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]">
                      <span>LIHAT ALOKASI PESANAN</span>
                      <ArrowRight size={26} strokeWidth={2.5} />
                    </button>
                  )}
                  {activeView === "commerce" && (
                    <Link href={`/impact?simulation=${simulationId}&condition=${encodeURIComponent(operationalCondition)}`} className="inline-flex min-h-[72px] w-full max-w-[620px] items-center justify-center gap-4 rounded-[32px] bg-[#eba92d] px-9 text-[18px] font-bold text-white shadow-sm transition hover:bg-[#d89a22] active:scale-[.98]">
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
