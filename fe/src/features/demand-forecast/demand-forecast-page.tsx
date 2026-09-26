"use client";
import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { DemandForecast } from "@/domain/demand-forecast";
import { useDemandForecast } from "@/hooks/use-demand-forecast";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { ForecastChart } from "./forecast-chart";
import { selectForecastPoints, type ForecastRange } from "./forecast-range";
import styles from "./demand-forecast.module.css";

function ForecastContent({ forecast, locale, onProduct }: { forecast: DemandForecast; locale: InventoryLocale; onProduct: (id: string) => void }) {
  const [range, setRange] = useState<ForecastRange>("future");
  return <>
    <div className={styles.filterHeader}>
      <div className={styles.controls}>
        <label><span className={styles.srOnly}>{locale === "en" ? "Product" : "Produk"}</span><select value={forecast.productId} onChange={(event) => onProduct(event.target.value)}>{(forecast.products ?? [{ id: forecast.productId, name: forecast.productName }]).map((product) => <option key={product.id} value={product.id}>{localizeInventoryTerm(product.name, locale)}</option>)}</select></label>
        <label><span className={styles.srOnly}>{locale === "en" ? "Chart range" : "Rentang grafik"}</span><select value={range} onChange={(event) => setRange(event.target.value as ForecastRange)}><option value="future">{locale === "en" ? "Next 3 Days" : "3 Hari ke Depan"}</option><option value="past">{locale === "en" ? "Previous 3 Days" : "3 Hari ke Belakang"}</option><option value="both">{locale === "en" ? "Both Ranges" : "Keduanya"}</option></select></label>
      </div>
      <div className={styles.totalBadge}>{locale === "en" ? "Total Forecast" : "Total Prediksi"}: {forecast.totalPredictedSales} {locale === "en" ? "Cups" : "Gelas"}</div>
    </div>
    {forecast.source === "api" && <>
      <details className={styles.forecastInfo}>
        <summary>{forecast.forecastSource === "FALLBACK" ? (locale === "en" ? "Estimated forecast · About this data" : "Prediksi estimasi · Tentang data ini") : forecast.forecastSource === "XGBOOST" ? (locale === "en" ? "Model forecast · About this data" : "Prediksi model · Tentang data ini") : (locale === "en" ? "About this forecast" : "Tentang prediksi ini")}</summary>
        {forecast.forecastSource === "FALLBACK" && <p>{locale === "en" ? "This estimate uses historical training patterns, not live XGBoost output. More recorded sales are needed for a model forecast." : "Estimasi ini memakai pola historis pelatihan, bukan hasil langsung XGBoost. Prediksi model memerlukan lebih banyak penjualan tercatat."}</p>}
        {forecast.forecastSource === "FALLBACK" && forecast.historyCoverage && <p>{locale === "en" ? `Recorded sales: ${forecast.historyCoverage.coveredDays} of ${forecast.historyCoverage.requiredDays} consecutive days. ` : `Penjualan tercatat: ${forecast.historyCoverage.coveredDays} dari ${forecast.historyCoverage.requiredDays} hari berturut-turut. `}<Link href="/penjualan">{locale === "en" ? "Import past sales" : "Impor riwayat penjualan"}</Link></p>}
        <p>{locale === "en" ? "Synthetic training data" : "Data pelatihan sintetis"}: {forecast.trainingDataSynthetic === true ? (locale === "en" ? "Yes" : "Ya") : forecast.trainingDataSynthetic === false ? (locale === "en" ? "No" : "Tidak") : (locale === "en" ? "Unknown" : "Tidak diketahui")}</p>
      </details>
    </>}
    <ForecastChart points={selectForecastPoints(forecast, range)} locale={locale} />
    <section className={styles.detailCard} aria-labelledby="forecast-detail-title">
      <h2 id="forecast-detail-title">{locale === "en" ? "Forecast & Material Requirements" : "Detail Prediksi & Kebutuhan Bahan"}</h2>
      <div className={styles.tableScroll}><table>
        <thead><tr><th>{locale === "en" ? "Date" : "Tanggal"}</th><th>{locale === "en" ? "Product" : "Produk"}</th><th>{locale === "en" ? "Sales Forecast" : "Prediksi Penjualan"}</th>{forecast.source === "mock" && <><th>{locale === "en" ? "Primary Material" : "Bahan Utama"}</th><th>{locale === "en" ? "Estimated Requirement" : "Kebutuhan Estimasi"}</th></>}</tr></thead>
        <tbody>{forecast.details.map((row) => <tr key={row.dateLabel}><td>{row.dateLabel}</td><td>{localizeInventoryTerm(row.productName, locale)}</td><td>{row.predictedSales} {locale === "en" ? "Cups" : "Gelas"}</td>{forecast.source === "mock" && <><td>{localizeInventoryTerm(row.primaryMaterial ?? "—", locale)}</td><td>{row.estimatedRequirement?.toFixed(1)} {row.unit}</td></>}</tr>)}</tbody>
      </table></div>
    </section>
  </>;
}
export function DemandForecastPage() {
  const [productId, setProductId] = useState<string>();
  const forecast = useDemandForecast(productId);
  const { locale } = useInventoryLanguage();
  return <InventoryShell title={locale === "en" ? "Demand Forecast" : "Prediksi Permintaan"} actions={<Link href="/stok-berisiko" className={styles.riskButton}><ShieldAlert aria-hidden="true" />{locale === "en" ? "View Your Stock Risks" : "Lihat Risiko Stok Anda"}</Link>}>
    <div className={styles.page}>
      {forecast.isLoading && <LoadingState label={locale === "en" ? "Loading demand forecast..." : "Memuat prediksi permintaan..."} />}
      {forecast.isError && <ErrorState message={forecast.error.message} onRetry={() => void forecast.refetch()} />}
      {forecast.data && !forecast.isError && (forecast.data.details.length === 0 ? <InventoryEmptyState page="forecast" locale={locale} /> : <ForecastContent forecast={forecast.data} locale={locale} onProduct={setProductId} />)}
    </div>
  </InventoryShell>;
}
