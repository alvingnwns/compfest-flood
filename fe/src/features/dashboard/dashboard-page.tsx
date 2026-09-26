"use client";

import { AlertTriangle } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { DashboardSummary, InventoryRiskStatus } from "@/domain/dashboard";
import { useDashboardSummary } from "@/hooks/use-dashboard-summary";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { DemandProjectionChart } from "./demand-projection-chart";
import { inventoryStatusLabel } from "@/lib/inventory-risk";
import styles from "./dashboard.module.css";

type Filter = "all" | InventoryRiskStatus;

const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

const metricLabels = {
  en: { "gross-sales": "Gross Sales", "products-sold": "Products Sold", "at-risk-materials": "At-Risk Materials", "pending-actions": "Pending Actions" },
  id: { "gross-sales": "Penjualan Kotor", "products-sold": "Produk Terjual", "at-risk-materials": "Bahan Berisiko", "pending-actions": "Tindakan Tertunda" },
};

function DailySummary({ metrics, locale }: { metrics: DashboardSummary["metrics"]; locale: InventoryLocale }) {
  return <section aria-labelledby="daily-summary-title"><h2 id="daily-summary-title" className={styles.sectionTitle}>{locale === "en" ? "Daily Summary" : "Ringkasan Harian"}</h2><div className={styles.metrics}>{metrics.map((metric) => <div key={metric.id} className={styles.metric}><p>{metricLabels[locale][metric.id]}</p><strong>{metric.format === "currency" ? rupiah.format(metric.value) : metric.value}</strong></div>)}</div></section>;
}

function PendingActions({ risks, locale, api }: { risks: DashboardSummary["inventoryRisks"]; locale: InventoryLocale; api: boolean }) {
  const filterValues: Filter[] = api ? ["all", "out-of-stock", "shortage-risk", "low-stock"] : ["all", "out-of-stock", "expiring", "surplus"];
  const [filter, setFilter] = useState<Filter>("all");
  const visibleRisks = useMemo(() => risks.filter((risk) => filter === "all" || risk.status === filter), [filter, risks]);
  const labels = filterValues.map((value) => value === "all" ? (locale === "en" ? "All" : "Semua") : inventoryStatusLabel(value, locale));

  return (
    <section className={styles.pendingActions} aria-labelledby="pending-actions-title">
      <h2 id="pending-actions-title" className={styles.sectionTitle}>{locale === "en" ? "Pending Actions" : "Tindakan Tertunda"}</h2>
      <div className={styles.filters} aria-label={locale === "en" ? "Pending action filters" : "Filter tindakan tertunda"}>{filterValues.map((value, index) => <button key={value} type="button" className={filter === value ? styles.filterActive : styles.filterButton} aria-pressed={filter === value} onClick={() => setFilter(value)}>{labels[index]}</button>)}</div>
      <div className={styles.tableCard} role="region" aria-label={locale === "en" ? "Pending actions table" : "Tabel tindakan tertunda"} tabIndex={0}>
        <table>
          <thead><tr><th>{locale === "en" ? "Material" : "Nama Bahan"}</th><th>{locale === "en" ? "Available" : "Tersedia"}</th><th>{locale === "en" ? "Forecast Demand" : "Prediksi Kebutuhan"} <span>({locale === "en" ? "3 Days" : "3 Hari"})</span></th><th>{locale === "en" ? "Issue" : "Masalah"}</th><th>{locale === "en" ? "Due" : "Waktu"}</th></tr></thead>
          <tbody>
            {visibleRisks.map((risk) => <tr key={risk.id}><td>{localizeInventoryTerm(risk.materialName, locale)}</td><td>{risk.availableQuantity} {risk.unit}</td><td>{risk.predictedDemand} {risk.unit}</td><td><span className={`${styles.status} ${risk.status === "out-of-stock" ? styles.danger : styles.warning}`}><AlertTriangle aria-hidden="true" />{inventoryStatusLabel(risk.status, locale)}</span></td><td className={risk.dueLabel === "Hari Ini" ? styles.dueNow : styles.dueSoon}>{localizeInventoryTerm(risk.dueLabel, locale)}</td></tr>)}
            {visibleRisks.length === 0 && <tr><td colSpan={5} className={styles.emptyRow}>{locale === "en" ? "No actions in this category." : "Tidak ada tindakan pada kategori ini."}</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PriorityActions({ recommendations, locale }: { recommendations: DashboardSummary["priorityRecommendations"]; locale: InventoryLocale }) {
  return (
    <aside className={styles.priorityCard} aria-labelledby="priority-title">
      <h2 id="priority-title" className={styles.sectionTitle}>{locale === "en" ? "Priority Actions" : "Tindakan Prioritas"}</h2>
      <div className={styles.recommendations}>{recommendations.slice(0, 2).map((item, index) => {
        const material = item.materialName ? localizeInventoryTerm(item.materialName, locale) : item.id === "ayam" ? (locale === "en" ? "Chicken" : "Ayam") : (locale === "en" ? "Tomato" : "Tomat");
        const title = item.materialName ? `${locale === "en" ? "Order" : "Pesan"} ${item.quantity} ${item.unit} ${material}` : item.title;
        const detail = item.detail;
        return <article key={item.id} className={styles.recommendation}><span className={styles.recommendationNumber}>{String(index + 1).padStart(2, "0")}</span><div><h3>{title}</h3><p>{detail}</p></div></article>;
      })}</div>
      <Link href="/rencana-optimasi" className={styles.viewMore}>{locale === "en" ? "View More" : "Lihat Lainnya"} &gt;&gt;</Link>
    </aside>
  );
}

export function DashboardPage() {
  const summary = useDashboardSummary();
  const { locale } = useInventoryLanguage();

  return (
    <InventoryShell title={locale === "en" ? "Overview" : "Ringkasan"}>
      <div className={styles.page}>
        {summary.isLoading && <LoadingState label={locale === "en" ? "Loading inventory overview..." : "Memuat ringkasan inventori..."} />}
        {summary.isError && <ErrorState message={locale === "en" ? "Inventory overview could not be loaded." : "Ringkasan inventori tidak dapat dimuat."} onRetry={() => void summary.refetch()} />}
        {summary.data && !summary.isError && (summary.data.hasInventoryData === false && summary.data.metrics.every((metric) => metric.value === 0) && summary.data.demandProjection.length === 0 && summary.data.priorityRecommendations.length === 0 ? <InventoryEmptyState page="overview" locale={locale} /> : <><DailySummary metrics={summary.data.metrics} locale={locale} /><div className={styles.dashboardGrid}><PendingActions risks={summary.data.inventoryRisks} locale={locale} api={summary.data.source === "api"} /><PriorityActions recommendations={summary.data.priorityRecommendations} locale={locale} /></div>{summary.data.demandProjection.length >= 2 && <DemandProjectionChart data={summary.data.demandProjection} locale={locale} />}</>)}
      </div>
    </InventoryShell>
  );
}
