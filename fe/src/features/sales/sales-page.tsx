"use client";

import { CalendarDays, ChevronDown, FileUp, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { SalesOverview, SalesTransaction } from "@/domain/sales";
import { useSalesOverview, useSalesTransaction } from "@/hooks/use-sales-overview";
import { usesInventoryApi } from "@/lib/inventory-api";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { SalesHistoryImport } from "./sales-history-import";
import styles from "./sales.module.css";

type SortKey = "id" | "occurredAt" | "cupCount" | "total";
const rupiah = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const time = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23", timeZone: "Asia/Jakarta" });

function SalesKpis({ data, locale }: { data: SalesOverview["summary"]; locale: InventoryLocale }) {
  const kpis = locale === "en"
    ? [["Today's Total Revenue", rupiah.format(data.revenue)], ["Transactions", `${data.transactionCount} Transactions`], ["Total Cups Sold", `${data.cupsSold} Cups`]]
    : [["Total Revenue Hari Ini", rupiah.format(data.revenue)], ["Jumlah Transaksi", `${data.transactionCount} Transaksi`], ["Total Gelas Terjual", `${data.cupsSold} Gelas`]];
  return <div className={styles.kpis}>{kpis.map(([label, value]) => <article key={label}><p>{label}</p><strong>{value}</strong></article>)}</div>;
}

function TransactionDetail({ transaction: selectedTransaction, locale, onClose }: { transaction: SalesTransaction; locale: InventoryLocale; onClose: () => void }) {
  const detail = useSalesTransaction(selectedTransaction.id);
  const transaction = detail.data ?? selectedTransaction;
  return (
    <aside className={styles.detail} aria-labelledby="transaction-detail-title">
      <div className={styles.detailTitle}><h2 id="transaction-detail-title">{locale === "en" ? "Transaction Details" : "Detail Transaksi"}</h2><button type="button" onClick={onClose} aria-label={locale === "en" ? "Close transaction details" : "Tutup detail transaksi"}><X /></button></div>
      {detail.isLoading && <LoadingState label={locale === "en" ? "Loading transaction..." : "Memuat transaksi..."} />}
      {detail.isError && <ErrorState message={detail.error.message} onRetry={() => void detail.refetch()} />}
      <div className={styles.receipt}>
        <strong>{transaction.id}</strong>
        <div className={styles.rule} />
        {transaction.items.map((item) => <div key={item.name} className={styles.receiptRow}><span>{localizeInventoryTerm(item.name, locale)} x{item.quantity}</span><span>{rupiah.format(item.quantity * item.unitPrice)}</span></div>)}
        <div className={styles.rule} />
        <div className={styles.receiptTotal}><span>{locale === "en" ? "Total Bill" : "Total Tagihan"}</span><strong>{rupiah.format(transaction.total)}</strong></div>
      </div>
      <div className={styles.deductions}>
        <h3>{locale === "en" ? "Material Stock Deductions:" : "Pengurangan Stok Bahan:"}</h3>
        {transaction.inventoryDeductions.map((item) => <div key={item.materialName}><span>{localizeInventoryTerm(item.materialName, locale)}</span><strong>-{item.quantity}{item.unit}</strong></div>)}
      </div>
      <div className={styles.status}>{locale === "en" ? "Status: Inventory Deducted" : "Status: Inventaris Dikurangi"}</div>
    </aside>
  );
}

function SalesContent({ overview, locale }: { overview: SalesOverview; locale: InventoryLocale }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; direction: "asc" | "desc" }>({ key: "occurredAt", direction: "desc" });
  const [selectedId, setSelectedId] = useState(overview.transactions[0]?.id ?? "");
  const [detailOpen, setDetailOpen] = useState(true);
  const transactions = useMemo(() => {
    const filtered = overview.transactions.filter((transaction) => transaction.id.toLowerCase().includes(query.trim().toLowerCase()));
    return [...filtered].sort((a, b) => {
      const left = a[sort.key]; const right = b[sort.key];
      const result = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right));
      return sort.direction === "asc" ? result : -result;
    });
  }, [overview.transactions, query, sort]);
  const selected = transactions.find((transaction) => transaction.id === selectedId) ?? transactions[0];
  const setSorting = (key: SortKey) => setSort((current) => ({ key, direction: current.key === key && current.direction === "asc" ? "desc" : "asc" }));
  const headers: Array<[string, SortKey]> = locale === "en" ? [["Transaction ID", "id"], ["Time", "occurredAt"], ["Cups", "cupCount"], ["Total", "total"]] : [["Transaksi ID", "id"], ["Waktu", "occurredAt"], ["Gelas", "cupCount"], ["Total", "total"]];

  return (
    <>
      <SalesKpis data={overview.summary} locale={locale} />
      <div className={styles.toolbar}>
        <label className={styles.search}><Search aria-hidden="true" /><span className={styles.srOnly}>{locale === "en" ? "Search transaction ID" : "Cari transaksi ID"}</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === "en" ? "Search transaction ID..." : "Cari transaksi ID..."} /></label>
        <div className={styles.date}><CalendarDays aria-hidden="true" /><span>{`${locale === "en" ? "Today" : "Hari Ini"} (${overview.businessDate})`}</span></div>
      </div>
      <div className={`${styles.contentGrid} ${detailOpen && selected ? "" : styles.detailClosed}`}>
        <section className={styles.tableCard} aria-label={locale === "en" ? "Sales transactions" : "Daftar transaksi penjualan"}>
          <div className={styles.tableScroll}><table><thead><tr>{headers.map(([label, key]) => <th key={key}><button type="button" onClick={() => setSorting(key)}>{label}<ChevronDown className={sort.key === key && sort.direction === "asc" ? styles.chevronUp : undefined} /></button></th>)}</tr></thead><tbody>
            {transactions.map((transaction) => <tr key={transaction.id} className={selected?.id === transaction.id && detailOpen ? styles.selectedRow : undefined} onClick={() => { setSelectedId(transaction.id); setDetailOpen(true); }}><td>{transaction.id}</td><td>{time.format(new Date(transaction.occurredAt))}</td><td>{transaction.cupCount}</td><td>{rupiah.format(transaction.total)}</td></tr>)}
            {transactions.length === 0 && <tr><td colSpan={4} className={styles.empty}>{locale === "en" ? "No transactions found." : "Transaksi tidak ditemukan."}</td></tr>}
          </tbody></table></div>
        </section>
        {detailOpen && selected && <TransactionDetail transaction={selected} locale={locale} onClose={() => setDetailOpen(false)} />}
      </div>
    </>
  );
}

export function SalesPage() {
  const overview = useSalesOverview();
  const { locale } = useInventoryLanguage();
  const [importOpen, setImportOpen] = useState(false);
  // Importing needs the real backend; mock data mode has nothing to import into.
  const importAction = usesInventoryApi()
    ? <button type="button" className={styles.importButton} aria-expanded={importOpen} onClick={() => setImportOpen((open) => !open)}><FileUp aria-hidden="true" />{locale === "en" ? "Import Sales History" : "Impor Riwayat Penjualan"}</button>
    : undefined;

  return (
    <InventoryShell title={locale === "en" ? "Sales" : "Penjualan"} actions={importAction}>
      <div className={styles.page}>
        {importOpen && <SalesHistoryImport locale={locale} onClose={() => setImportOpen(false)} />}
        {overview.isLoading && <LoadingState label={locale === "en" ? "Loading sales data..." : "Memuat data penjualan..."} />}
        {overview.isError && <ErrorState message={locale === "en" ? "Sales data could not be loaded." : "Data penjualan tidak dapat dimuat."} onRetry={() => void overview.refetch()} />}
        {overview.data && !overview.isError && (overview.data.transactions.length === 0 ? <InventoryEmptyState page="sales" locale={locale} /> : <SalesContent overview={overview.data} locale={locale} />)}
      </div>
    </InventoryShell>
  );
}
