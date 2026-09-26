"use client";

import { AlertTriangle, Settings2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { StockRiskMaterial, StockRiskOverview } from "@/domain/stock-risk";
import { useStockRisk } from "@/hooks/use-stock-risk";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { inventoryStatusLabel } from "@/lib/inventory-risk";
import styles from "./stock-risk.module.css";

const statusClasses: Record<StockRiskMaterial["status"], string> = {
  "out-of-stock": styles.critical,
  "low-stock": styles.warning,
  "shortage-risk": styles.critical,
  surplus: styles.surplus,
  normal: styles.normal,
};

const quantity = (value: number, unit: string) => `${value.toFixed(1)} ${unit}`;
const difference = (value: number, unit: string) => `${value > 0 ? "+" : ""}${value.toFixed(1)} ${unit}`;

function RiskTable({ materials, selectedId, locale, onSelect }: { materials: StockRiskMaterial[]; selectedId: string; locale: InventoryLocale; onSelect: (id: string) => void }) {
  return (
    <div className={styles.tableScroll}>
      <table>
        <thead><tr><th>{locale === "en" ? "Material" : "Bahan"}</th><th>{locale === "en" ? "Stock" : "Stok"}</th><th>{locale === "en" ? "Forecast" : "Prediksi"}</th><th>{locale === "en" ? "Difference" : "Selisih"}</th><th>Status</th></tr></thead>
        <tbody>
          {materials.map((material) => (
            <tr key={material.id} className={selectedId === material.id ? styles.selectedRow : undefined}>
              <td><button type="button" className={styles.rowButton} onClick={() => onSelect(material.id)} aria-pressed={selectedId === material.id}>{localizeInventoryTerm(material.name, locale)}</button></td>
              <td>{quantity(material.currentStock, material.unit)}</td>
              <td>{quantity(material.predictedNeed, material.unit)}</td>
              <td className={statusClasses[material.status]}><strong>{difference(material.difference, material.unit)}</strong></td>
              <td><span className={`${styles.statusBadge} ${statusClasses[material.status]}`}>{inventoryStatusLabel(material.status, locale)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskDetail({ material, locale }: { material: StockRiskMaterial; locale: InventoryLocale }) {
  const shortage = Math.max(0, -material.difference);

  return (
    <aside className={styles.detailCard} aria-labelledby="risk-detail-title">
      <div className={styles.detailHeading}>
        <AlertTriangle aria-hidden="true" />
        <h2 id="risk-detail-title">{locale === "en" ? <>Risk Analysis<br />Details</> : <>Analisis<br />Detail Risiko</>}</h2>
      </div>
      <h3>{localizeInventoryTerm(material.name, locale)}</h3>
      <dl>
        <div><dt>{locale === "en" ? "Active Warehouse Stock" : "Stok Gudang Aktif"}</dt><dd>{quantity(material.currentStock, material.unit)}</dd></div>
        <div><dt>{locale === "en" ? "Supplier Lead Time" : "Waktu Tunggu Pemasok"}</dt><dd>{locale === "en" ? material.restockLeadTime.replace("Hari Kerja", "Business Day") : material.restockLeadTime}</dd></div>
        <div><dt>{locale === "en" ? "Stock Shortage" : "Kekurangan Stok"}</dt><dd className={shortage > 0 ? styles.critical : styles.normal}>{quantity(shortage, material.unit)}</dd></div>
      </dl>
      {material.riskReason && <p>{material.riskReason}</p>}
    </aside>
  );
}

function StockProjection({ materials, locale }: { materials: StockRiskMaterial[]; locale: InventoryLocale }) {
  const maximum = Math.max(...materials.flatMap((material) => [material.currentStock, material.predictedNeed]), 1);

  return (
    <section className={styles.projectionCard} aria-labelledby="projection-title">
      <h2 id="projection-title">{locale === "en" ? "Stock vs Demand Projection" : "Proyeksi Stok vs Kebutuhan"}</h2>
      <div className={styles.barChart} role="img" aria-label={locale === "en" ? "Current stock and forecast demand comparison by material" : "Perbandingan stok saat ini dan prediksi kebutuhan setiap bahan"}>
        {materials.map((material) => (
          <div className={styles.barRow} key={material.id}>
            <span>{localizeInventoryTerm(material.name, locale)}</span>
            <div className={styles.bars}>
              <i className={styles.stockBar} style={{ width: `${Math.max(2, material.currentStock / maximum * 100)}%` }} />
              <i className={styles.needBar} style={{ width: `${Math.max(2, material.predictedNeed / maximum * 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className={styles.legend}>
        <span><i className={styles.stockKey} />{locale === "en" ? "Current Stock" : "Stok Saat Ini"}</span>
        <span><i className={styles.needKey} />{locale === "en" ? "Forecast Demand" : "Prediksi Kebutuhan"}</span>
      </div>
      <Link href="/rencana-optimasi" className={styles.orderButton}>{locale === "en" ? "View Order Recommendations" : "Lihat Rekomendasi Pesanan"}</Link>
    </section>
  );
}

function StockRiskContent({ overview, locale }: { overview: StockRiskOverview; locale: InventoryLocale }) {
  const [selectedId, setSelectedId] = useState(overview.materials[0]?.id ?? "");
  const selected = overview.materials.find((material) => material.id === selectedId) ?? overview.materials[0];

  if (!selected) return <InventoryEmptyState page="risk" locale={locale} />;
  return (
    <>
      <div className={styles.topGrid}>
        <section className={styles.tableCard} aria-labelledby="risk-list-title">
          <h2 id="risk-list-title">{locale === "en" ? "Raw Material Risk Analysis" : "Daftar Analisis Risiko Bahan Baku"}</h2>
          <RiskTable materials={overview.materials} selectedId={selected.id} locale={locale} onSelect={setSelectedId} />
        </section>
        <RiskDetail material={selected} locale={locale} />
      </div>
      <StockProjection materials={overview.materials} locale={locale} />
    </>
  );
}

export function StockRiskPage() {
  const overview = useStockRisk();
  const { locale } = useInventoryLanguage();
  const action = <Link href="/rencana-optimasi" className={styles.optimizationButton}><Settings2 aria-hidden="true" />{locale === "en" ? "Create Optimization" : "Buat Optimasi"}</Link>;

  return (
    <InventoryShell title={locale === "en" ? "Stock Risks" : "Stok Berisiko"} actions={action}>
      <div className={styles.page}>
        {overview.isLoading && <LoadingState label={locale === "en" ? "Loading stock risk analysis…" : "Memuat analisis risiko stok…"} />}
        {overview.isError && <ErrorState message={locale === "en" ? "Stock risk analysis could not be loaded." : "Analisis risiko stok tidak dapat dimuat."} onRetry={() => void overview.refetch()} />}
        {overview.data && !overview.isError && <StockRiskContent overview={overview.data} locale={locale} />}
      </div>
    </InventoryShell>
  );
}
