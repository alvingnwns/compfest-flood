"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useId } from "react";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import styles from "./inventory-page-state.module.css";

type Page = "overview" | "sales" | "stock" | "movements" | "forecast" | "risk" | "optimization" | "pos";
const content: Record<Page, { image: "overview" | "sales" | "inventory" | "forecast"; en: [string, string]; id: [string, string]; href?: string; action?: [string, string] }> = {
  overview: { image: "overview", en: ["No data yet", "Start recording sales and inventory to see your daily overview and insights here."], id: ["Belum Ada Data", "Mulai catat penjualan dan inventaris Anda untuk melihat ringkasan dan analisis di sini."], href: "/pos-simulator", action: ["Open POS Simulator", "Buka POS Simulator"] },
  sales: { image: "sales", en: ["No sales today", "Completed transactions will appear here. Record your first sale using the POS Simulator."], id: ["Belum Ada Penjualan Hari Ini", "Transaksi selesai akan muncul di sini. Catat penjualan pertama melalui POS Simulator."], href: "/pos-simulator", action: ["Record a Sale", "Catat Penjualan"] },
  stock: { image: "inventory", en: ["No inventory data", "No ingredients are configured yet. Configure your ingredient catalogue before receiving stock."], id: ["Belum Ada Data Inventaris", "Belum ada bahan yang dikonfigurasi. Siapkan katalog bahan sebelum menerima stok."] },
  movements: { image: "inventory", en: ["No stock movements yet", "Sales, physical receiving and stock adjustments will appear here once recorded."], id: ["Belum Ada Pergerakan Stok", "Penjualan, penerimaan fisik, dan penyesuaian stok akan muncul di sini setelah dicatat."] },
  forecast: { image: "forecast", en: ["No forecast available yet", "Your three-day demand forecast will appear when product and forecast data are available."], id: ["Belum Ada Perkiraan", "Prediksi permintaan tiga hari akan muncul setelah data produk dan prediksi tersedia."], href: "/pos-simulator", action: ["View POS Simulator", "Lihat POS Simulator"] },
  risk: { image: "forecast", en: ["No stock data to analyze", "Inventory and demand data are needed to identify ingredients at risk of running out."], id: ["Belum Ada Data Risiko Stok", "Data inventaris dan kebutuhan diperlukan untuk mengidentifikasi bahan yang berisiko habis."], href: "/gudang", action: ["View Inventory", "Lihat Gudang"] },
  optimization: { image: "forecast", en: ["No optimization recommendations", "There are no restock recommendations in this plan. Review inventory and supplier availability before purchasing."], id: ["Belum Ada Rekomendasi Optimasi", "Belum ada rekomendasi restok pada rencana ini. Periksa inventaris dan ketersediaan pemasok sebelum membeli."], href: "/gudang", action: ["View Inventory", "Lihat Gudang"] },
  pos: { image: "forecast", en: ["No products available", "Configure active products and their recipes before recording a simulated sale."], id: ["Belum Ada Produk", "Konfigurasikan produk aktif dan resepnya sebelum mencatat simulasi penjualan."] },
};
const dimensions = { overview: [240, 240], sales: [194, 197], inventory: [160, 160], forecast: [144, 144] } as const;

export function InventoryEmptyState({ page, locale, action }: { page: Page; locale: InventoryLocale; action?: { label: string; onClick: () => void } }) {
  const config = content[page];
  const titleId = useId();
  const [title, message] = config[locale];
  const [width, height] = dimensions[config.image];
  const label = action?.label ?? config.action?.[locale === "en" ? 0 : 1];
  const actionContent = <><Image src="/inventory-states/plus.svg" alt="" width={24} height={24} />{label}</>;
  return <section className={styles.empty} aria-labelledby={titleId}>
    <Image className={styles.illustration} src={`/inventory-states/${config.image}.png`} alt="" width={width} height={height} />
    <div className={styles.copy}><h2 id={titleId}>{title}</h2><p>{message}</p></div>
    {action ? <button type="button" className={styles.action} onClick={action.onClick}>{actionContent}</button> : config.href && <Link className={styles.action} href={config.href}>{actionContent}</Link>}
  </section>;
}

export function LoadingState({ label }: { label?: string }) {
  const { locale } = useInventoryLanguage();
  return <section className={styles.loading} role="status" aria-busy="true" aria-label={label ?? (locale === "en" ? "Loading data" : "Memuat data")}>
    <p className={styles.loadingLabel}>{label ?? (locale === "en" ? "Loading data..." : "Memuat data...")}</p>
    <div aria-hidden="true" className={styles.skeleton}><div className={styles.skeletonMetrics}>{[0, 1, 2].map((item) => <div key={item} />)}</div><div className={styles.skeletonPanel}>{[0, 1, 2, 3].map((item) => <div key={item} />)}</div></div>
  </section>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { locale } = useInventoryLanguage();
  return <section className={styles.error} role="alert"><AlertTriangle aria-hidden="true" /><h2>{locale === "en" ? "Unable to load data" : "Data Gagal Dimuat"}</h2><p>{message}</p>{onRetry && <button type="button" className={styles.retry} onClick={onRetry}><RefreshCw size={16} aria-hidden="true" />{locale === "en" ? "Try Again" : "Coba Lagi"}</button>}</section>;
}
