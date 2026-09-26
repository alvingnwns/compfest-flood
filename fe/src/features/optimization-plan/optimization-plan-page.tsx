"use client";

import { FileText } from "lucide-react";
import { useMemo, useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { OptimizationAction, OptimizationPlan, OptimizationStatus } from "@/domain/optimization-plan";
import { useOptimizationPlan, usePlanDecision } from "@/hooks/use-optimization-plan";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { StockMutationForm } from "@/features/inventory/stock-mutation-form";
import styles from "./optimization-plan.module.css";

const statuses: OptimizationStatus[] = ["pending", "approved", "completed", "dismissed"];
const statusLabels = {
  en: { pending: "Pending", approved: "Approved", completed: "Completed", dismissed: "Dismissed" },
  id: { pending: "Menunggu", approved: "Disetujui", completed: "Selesai", dismissed: "Diabaikan" },
};
const priorityLabels = {
  en: { high: "High", medium: "Medium", low: "Low" },
  id: { high: "Tinggi", medium: "Sedang", low: "Rendah" },
};

function actionLabel(action: OptimizationAction["action"], locale: InventoryLocale) {
  if (locale === "en") return action === "restock" ? "Restock Material" : "Reduce Purchase";
  return action === "restock" ? "Restok Bahan" : "Kurangi Pembelian";
}

function indonesianRationale(action: OptimizationAction) {
  const material = localizeInventoryTerm(action.materialName, "id");
  if (action.action === "reduce-purchase") return `Stok ${material} saat ini melebihi prediksi kebutuhan. Mengurangi pembelian berikutnya sebesar ${action.quantity.toFixed(1)} ${action.unit} dapat membatasi kelebihan stok.`;
  return `Sistem mendeteksi risiko kekurangan ${material} sebesar ${action.shortage.toFixed(1)} ${action.unit}. Direkomendasikan melakukan restok ${action.quantity.toFixed(1)} ${action.unit} untuk menjaga tingkat operasional yang aman.`;
}

function RecommendationTable({ actions, selectedId, locale, onSelect }: { actions: OptimizationAction[]; selectedId: string; locale: InventoryLocale; onSelect: (id: string) => void }) {
  return (
    <div className={styles.tableScroll}>
      <table>
        <thead><tr><th>{locale === "en" ? "Action" : "Tindakan"}</th><th>{locale === "en" ? "Material" : "Bahan"}</th><th>{locale === "en" ? "Quantity" : "Jumlah"}</th><th>{locale === "en" ? "Deadline" : "Batas Waktu"}</th><th>{locale === "en" ? "Priority" : "Prioritas"}</th></tr></thead>
        <tbody>
          {actions.map((action) => (
            <tr key={action.id} className={selectedId === action.id ? styles.selectedRow : undefined}>
              <td><button type="button" className={styles.rowButton} onClick={() => onSelect(action.id)} aria-pressed={selectedId === action.id}>{actionLabel(action.action, locale)}</button></td>
              <td>{localizeInventoryTerm(action.materialName, locale)}</td>
              <td><strong>{action.quantity.toFixed(1)} {action.unit}</strong></td>
              <td>{action.deadline}</td>
              <td><span className={`${styles.priority} ${styles[action.priority]}`}>{priorityLabels[locale][action.priority]}</span></td>
            </tr>
          ))}
          {actions.length === 0 && <tr><td colSpan={5} className={styles.empty}>{locale === "en" ? "No plans in this status." : "Tidak ada rencana dengan status ini."}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function ApprovalPanel({ action, locale, api }: { action: OptimizationAction | undefined; locale: InventoryLocale; api: boolean }) {
  const decision = usePlanDecision();
  const [receiving, setReceiving] = useState(false);
  const decide = (value: "APPROVED" | "REJECTED") => { if (action && !decision.isPending) decision.mutate({ id: action.id, decision: value }); };
  if (!action) return <aside className={styles.detailCard}><div className={styles.emptyDetail}>{locale === "en" ? "Select a plan to view its details." : "Pilih rencana untuk melihat detailnya."}</div></aside>;

  return (
    <aside className={styles.detailCard} aria-labelledby="approval-title">
      <div className={styles.detailHeading}><h2 id="approval-title">{locale === "en" ? "Plan Approval Form" : "Form Persetujuan Rencana"}</h2><FileText aria-hidden="true" /></div>
      <h3>{actionLabel(action.action, locale)} {localizeInventoryTerm(action.materialName, locale)}</h3>
      {api && <>
        <h4>{locale === "en" ? "Operational facts" : "Fakta operasional"}</h4>
        <p>{locale === "en" ? "Risk" : "Risiko"}: {action.riskLevel}</p>
        <p>{locale === "en" ? "Order date" : "Tanggal pemesanan"}: {action.deadline}</p>
        <h4>{locale === "en" ? "Explanation" : "Penjelasan"} ({action.explanationSource})</h4>
        <p>{locale === "en" ? "Explanation only. Use the structured quantity, supplier, timing and cost for decisions." : "Penjelasan saja. Gunakan jumlah, pemasok, waktu, dan biaya terstruktur untuk keputusan."}</p>
      </>}
      <p>{api || locale === "en" ? action.rationale : indonesianRationale(action)}</p>
      <div className={styles.rule} />
      <label className={styles.quantityField}>
        <span>{locale === "en" ? `Proposed Quantity (${action.unit})` : `Usulan Jumlah (${action.unit})`}</span>
        <input type="number" min="0" step="0.1" value={action.quantity} readOnly />
      </label>
      <div className={styles.actions}>
        <button type="button" className={styles.approveButton} disabled={!api || decision.isPending || action.status !== "pending"} onClick={() => decide("APPROVED")}>{locale === "en" ? "Approve Plan" : "Setujui Rencana"}</button>
        <button type="button" className={styles.dismissButton} disabled={!api || decision.isPending || action.status !== "pending"} onClick={() => decide("REJECTED")}>{locale === "en" ? "Reject" : "Tolak"}</button>
      </div>
      {decision.isPending && <p role="status">{locale === "en" ? "Saving decision..." : "Menyimpan keputusan..."}</p>}
      {decision.error && <p role="alert">{decision.error.message}</p>}
      {action.supplierName && <p>{locale === "en" ? "Supplier" : "Pemasok"}: {action.supplierName}</p>}
      {action.estimatedCost != null && <p>{locale === "en" ? "Estimated cost" : "Estimasi biaya"}: Rp {action.estimatedCost.toLocaleString("id-ID")}</p>}
      {action.expectedArrivalAt && <p>{locale === "en" ? "Expected arrival" : "Perkiraan tiba"}: {new Date(action.expectedArrivalAt).toLocaleString(locale === "en" ? "en-GB" : "id-ID", { timeZone: "Asia/Jakarta" })}</p>}
      {api && <p>{locale === "en" ? "Approval records your decision. Stock changes only after physical receiving." : "Persetujuan mencatat keputusan Anda. Stok berubah hanya setelah penerimaan fisik."}</p>}
      {api && action.receivedQuantity !== undefined && <p>{locale === "en" ? "Received" : "Sudah diterima"}: {action.receivedQuantity} {action.unit} · {locale === "en" ? "Outstanding" : "Belum diterima"}: {action.outstandingQuantity} {action.unit}</p>}
      {api && action.status === "approved" && (action.outstandingQuantity ?? action.quantity) > 0 && <button type="button" className={styles.approveButton} onClick={() => setReceiving(true)}>{locale === "en" ? "Receive Stock" : "Terima Stok"}</button>}
      {receiving && action.ingredientId && <StockMutationForm materials={[{ id: action.ingredientId, name: action.materialName, unit: action.unit, quantity: 0 }]} mode="receive" locale={locale} supplierId={action.supplierId} recommendationId={action.id} suggestedQuantity={action.outstandingQuantity ?? action.quantity} onClose={() => setReceiving(false)} />}
    </aside>
  );
}

function OptimizationContent({ plan, locale }: { plan: OptimizationPlan; locale: InventoryLocale }) {
  const [status, setStatus] = useState<OptimizationStatus>("pending");
  const [selectedId, setSelectedId] = useState(plan.actions.find((action) => action.status === "pending")?.id ?? "");
  const filtered = useMemo(() => plan.actions.filter((action) => action.status === status), [plan.actions, status]);
  const selected = filtered.find((action) => action.id === selectedId) ?? filtered[0];

  const changeStatus = (next: OptimizationStatus) => {
    setStatus(next);
    setSelectedId(plan.actions.find((action) => action.status === next)?.id ?? "");
  };

  return (
    <>
      <div className={styles.tabs} role="tablist" aria-label={locale === "en" ? "Optimization status" : "Status optimasi"}>
        {statuses.filter((item) => plan.source === "mock" || item !== "completed").map((item) => <button key={item} type="button" role="tab" aria-selected={status === item} className={status === item ? styles.activeTab : undefined} onClick={() => changeStatus(item)}>{statusLabels[locale][item]}</button>)}
      </div>
      {(plan.outcome === "INFEASIBLE" || plan.optimizerStatus === "INFEASIBLE") && <p role="status">{locale === "en" ? "No feasible purchasing plan is available. Review stock needs and supplier availability." : "Belum ada rencana pembelian yang dapat dijalankan. Periksa kebutuhan stok dan ketersediaan pemasok."}</p>}
      {plan.outcome === "PARTIAL" && <p role="status">{locale === "en" ? "This plan covers only part of the stock requirement. Review remaining needs before purchasing." : "Rencana ini hanya memenuhi sebagian kebutuhan stok. Periksa kebutuhan tersisa sebelum membeli."}</p>}
      {plan.actions.length === 0 ? <InventoryEmptyState page="optimization" locale={locale} /> : <div className={styles.contentGrid}>
        <section className={styles.tableCard} aria-labelledby="recommendation-title">
          <h2 id="recommendation-title">{locale === "en" ? "System Optimization Recommendations" : "Saran Tindakan Optimasi Sistem"}</h2>
          <RecommendationTable actions={filtered} selectedId={selected?.id ?? ""} locale={locale} onSelect={setSelectedId} />
        </section>
        <ApprovalPanel key={selected?.id ?? status} action={selected} locale={locale} api={plan.source === "api"} />
      </div>}
    </>
  );
}

export function OptimizationPlanPage() {
  const plan = useOptimizationPlan();
  const { locale } = useInventoryLanguage();

  return (
    <InventoryShell title={locale === "en" ? "Optimization Plan" : "Rencana Optimasi"}>
      <div className={styles.page}>
        {plan.isLoading && <LoadingState label={locale === "en" ? "Loading optimization plan..." : "Memuat rencana optimasi..."} />}
        {plan.isError && <ErrorState message={locale === "en" ? "Optimization plan could not be loaded." : "Rencana optimasi tidak dapat dimuat."} onRetry={() => void plan.refetch()} />}
        {plan.data && !plan.isError && <OptimizationContent plan={plan.data} locale={locale} />}
      </div>
    </InventoryShell>
  );
}
