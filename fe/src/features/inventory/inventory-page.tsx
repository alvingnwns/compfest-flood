"use client";

import { AlertTriangle, CalendarDays, ChevronDown, PackagePlus, Search, SlidersHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { InventoryOverview, MaterialStock, StockMovement } from "@/domain/inventory";
import { useInventoryOverview } from "@/hooks/use-inventory-overview";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import { inventoryStatusLabel } from "@/lib/inventory-risk";
import { StockMutationForm } from "./stock-mutation-form";
import styles from "./inventory.module.css";

type View = "stock" | "movements";
type MovementSortKey = "materialName" | "category" | "quantityChange" | "referenceId" | "occurredAt";

const time = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Asia/Jakarta" });

function SortHeader({ label, sortKey, activeKey, ascending, onSort }: { label: string; sortKey: MovementSortKey; activeKey: MovementSortKey; ascending: boolean; onSort: (key: MovementSortKey) => void }) {
  return <th><button type="button" onClick={() => onSort(sortKey)}>{label}<ChevronDown className={activeKey === sortKey && ascending ? styles.chevronUp : undefined} /></button></th>;
}

function MovementTable({ rows, selectedId, sortKey, ascending, locale, onSort, onSelect }: { rows: StockMovement[]; selectedId: string; sortKey: MovementSortKey; ascending: boolean; locale: InventoryLocale; onSort: (key: MovementSortKey) => void; onSelect: (id: string) => void }) {
  return (
    <div className={styles.tableViewport}>
      <table>
        <thead><tr><SortHeader label={locale === "en" ? "Material" : "Nama Bahan"} sortKey="materialName" activeKey={sortKey} ascending={ascending} onSort={onSort} /><SortHeader label={locale === "en" ? "Category" : "Kategori"} sortKey="category" activeKey={sortKey} ascending={ascending} onSort={onSort} /><SortHeader label={locale === "en" ? "Stock Change" : "Perubahan Stok"} sortKey="quantityChange" activeKey={sortKey} ascending={ascending} onSort={onSort} /><SortHeader label={locale === "en" ? "Transaction ID" : "Transaksi ID"} sortKey="referenceId" activeKey={sortKey} ascending={ascending} onSort={onSort} /><SortHeader label={locale === "en" ? "Time" : "Waktu"} sortKey="occurredAt" activeKey={sortKey} ascending={ascending} onSort={onSort} /></tr></thead>
        <tbody>
          {rows.map((row) => <tr key={row.id} className={row.id === selectedId ? styles.selected : undefined} onClick={() => onSelect(row.id)}>
            <td><span className={styles.materialCell}>{row.warningLevel && <AlertTriangle aria-label={row.warningLevel === "critical" ? (locale === "en" ? "Critical stock" : "Stok kritis") : (locale === "en" ? "Low stock" : "Stok menipis")} className={row.warningLevel === "critical" ? styles.critical : styles.warning} />}<strong>{localizeInventoryTerm(row.materialName, locale)}</strong></span></td>
            <td>{localizeInventoryTerm(row.category, locale)}</td><td>{row.quantityChange > 0 ? "+" : ""}{row.quantityChange} {row.unit}</td><td>{row.referenceId}</td><td>{time.format(new Date(row.occurredAt))}</td>
          </tr>)}
          {rows.length === 0 && <tr><td colSpan={5} className={styles.empty}>{locale === "en" ? "No materials found." : "Bahan tidak ditemukan."}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function StockTable({ rows, selectedId, locale, onSelect }: { rows: MaterialStock[]; selectedId: string; locale: InventoryLocale; onSelect: (id: string) => void }) {
  return (
    <div className={styles.tableViewport}>
      <table>
        <thead><tr><th>{locale === "en" ? "Material" : "Nama Bahan"}</th><th>{locale === "en" ? "Available" : "Tersedia"}</th><th>{locale === "en" ? "Forecast Demand" : "Prediksi Kebutuhan"}</th><th>{locale === "en" ? "Issue" : "Masalah"}</th><th>{locale === "en" ? "Due" : "Waktu"}</th></tr></thead>
        <tbody>
          {rows.map((row) => <tr key={row.id} className={row.id === selectedId ? styles.selected : undefined} onClick={() => onSelect(row.id)}>
            <td><span className={styles.materialCell}>{["out-of-stock", "low-stock"].includes(row.issue) && <AlertTriangle aria-label={row.issue === "out-of-stock" ? (locale === "en" ? "Critical stock" : "Stok kritis") : (locale === "en" ? "Low stock" : "Stok menipis")} className={row.issue === "out-of-stock" ? styles.critical : styles.warning} />}<strong>{localizeInventoryTerm(row.name, locale)}</strong></span></td>
            <td>{row.quantity} {row.unit}</td><td>{row.predictedDemand} {row.unit}</td><td>{inventoryStatusLabel(row.issue, locale)}</td><td>{localizeInventoryTerm(row.dueLabel, locale)}</td>
          </tr>)}
          {rows.length === 0 && <tr><td colSpan={5} className={styles.empty}>{locale === "en" ? "No materials found." : "Bahan tidak ditemukan."}</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function StockDetail({ material, locale, onClose, onAdjust }: { material: MaterialStock; locale: InventoryLocale; onClose: () => void; onAdjust: () => void }) {
  return (
    <aside className={styles.stockDetail} aria-labelledby="stock-detail-title">
      <div className={styles.stockDetailTitle}><h2 id="stock-detail-title">{localizeInventoryTerm(material.name, locale)}</h2><button type="button" onClick={onClose} aria-label={locale === "en" ? "Close material details" : "Tutup detail bahan"}><X /></button></div>
      <h3>{locale === "en" ? "Remaining Stock" : "Sisa Stok"}</h3>
      <div className={styles.stockFacts}>
        <span>{locale === "en" ? "Stock ID" : "Stok ID"}</span><span>{locale === "en" ? "Quantity" : "Kuantitas"}</span><span>{locale === "en" ? "Due" : "Waktu"}</span>
        <strong>{material.stockId}</strong><strong>{material.quantity} {material.unit}</strong><strong>{localizeInventoryTerm(material.dueLabel, locale)}</strong>
      </div>
      <div className={styles.supplier}><span>Supplier</span><strong>{material.supplier}</strong></div>
      <button type="button" className={styles.detailAdjust} onClick={onAdjust}>{locale === "en" ? "Adjust Stock" : "Sesuaikan Stok"}</button>
    </aside>
  );
}

function InventoryContent({ overview, view, locale, onViewChange }: { overview: InventoryOverview; view: View; locale: InventoryLocale; onViewChange: (view: View) => void }) {
  const [query, setQuery] = useState("");
  const [adjusting, setAdjusting] = useState<MaterialStock>();
  const [sort, setSort] = useState<{ key: MovementSortKey; ascending: boolean }>({ key: "occurredAt", ascending: false });
  const [selectedId, setSelectedId] = useState(overview.movements[0]?.id ?? "");
  const [selectedMaterialId, setSelectedMaterialId] = useState(overview.materials[0]?.id ?? "");
  const [stockDetailOpen, setStockDetailOpen] = useState(true);

  const movements = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = overview.movements.filter((row) => (row.materialName.toLowerCase().includes(needle) || localizeInventoryTerm(row.materialName, locale).toLowerCase().includes(needle)));
    return [...filtered].sort((a, b) => {
      const left = a[sort.key];
      const right = b[sort.key];
      const result = typeof left === "number" && typeof right === "number" ? left - right : String(left).localeCompare(String(right));
      return sort.ascending ? result : -result;
    });
  }, [overview.movements, query, sort, locale]);
  const materials = useMemo(() => overview.materials.filter((row) => (row.name.toLowerCase().includes(query.trim().toLowerCase()) || localizeInventoryTerm(row.name, locale).toLowerCase().includes(query.trim().toLowerCase()))), [overview.materials, query, locale]);
  const selected = movements.find((row) => row.id === selectedId) ?? movements[0];
  const selectedMaterial = materials.find((row) => row.id === selectedMaterialId) ?? materials[0];
  const onSort = (key: MovementSortKey) => setSort((current) => ({ key, ascending: current.key === key ? !current.ascending : true }));
  const movementSummary = selected ? `${selected.referenceId}   |   ${localizeInventoryTerm(selected.materialName, locale)} x ${Math.abs(selected.quantityChange)}   |   ${locale === "en" ? (selected.category === "Stok Masuk" ? "Stock increased" : selected.category === "Rusak" ? "Damaged stock" : "Stock decreased") : (selected.category === "Stok Masuk" ? "Stok bertambah" : selected.category === "Rusak" ? "Stok rusak" : "Stok berkurang")} ${Math.abs(selected.quantityChange)} ${selected.unit}` : (locale === "en" ? "Select a stock movement" : "Pilih pergerakan stok");

  return (
    <>
      <div className={styles.tabs} role="tablist" aria-label={locale === "en" ? "Inventory view" : "Tampilan gudang"}>
        <button type="button" role="tab" aria-selected={view === "stock"} className={view === "stock" ? styles.activeTab : undefined} onClick={() => onViewChange("stock")}>{locale === "en" ? "Material Stock" : "Stok Bahan"}</button>
        <button type="button" role="tab" aria-selected={view === "movements"} className={view === "movements" ? styles.activeTab : undefined} onClick={() => onViewChange("movements")}>{locale === "en" ? "Stock Movements" : "Pergerakan Stok"}</button>
      </div>
      <div className={view === "stock" ? `${styles.toolbar} ${styles.stockToolbar}` : styles.toolbar}>
        {view === "movements" && <div className={styles.date}><CalendarDays aria-hidden="true" /><span>{locale === "en" ? "All movements" : "Semua pergerakan"}</span></div>}
        <label className={styles.search}><Search aria-hidden="true" /><span className={styles.srOnly}>{locale === "en" ? "Search material name" : "Cari nama bahan"}</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === "en" ? "Enter material name..." : "Masukkan nama bahan..."} /></label>

      </div>
      {(view === "stock" ? overview.materials.length : overview.movements.length) === 0 ? <InventoryEmptyState page={view === "stock" ? "stock" : "movements"} locale={locale} action={view === "movements" ? { label: locale === "en" ? "View Material Stock" : "Lihat Stok Bahan", onClick: () => onViewChange("stock") } : undefined} /> : view === "movements" ? (
        <>
          <h2>{locale === "en" ? "Stock Movements" : "Pergerakan Stok"}</h2>
          <section className={styles.tableCard} aria-label={locale === "en" ? "Warehouse stock movements" : "Pergerakan stok gudang"}><MovementTable rows={movements} selectedId={selected?.id ?? ""} sortKey={sort.key} ascending={sort.ascending} locale={locale} onSort={onSort} onSelect={setSelectedId} /></section>
          <div className={styles.summaryBar}>{movementSummary}</div>
        </>
      ) : (
        <div className={`${styles.stockGrid} ${stockDetailOpen && selectedMaterial ? "" : styles.stockDetailClosed}`}>
          <section className={styles.tableCard} aria-label={locale === "en" ? "Warehouse material stock" : "Stok bahan gudang"}><StockTable rows={materials} selectedId={selectedMaterial?.id ?? ""} locale={locale} onSelect={(id) => { setSelectedMaterialId(id); setStockDetailOpen(true); }} /></section>
          {stockDetailOpen && selectedMaterial && <StockDetail material={selectedMaterial} locale={locale} onClose={() => setStockDetailOpen(false)} onAdjust={() => setAdjusting(selectedMaterial)} />}
        </div>
      )}
      {adjusting && <StockMutationForm materials={[adjusting]} mode="adjust" locale={locale} onClose={() => setAdjusting(undefined)} />}
    </>
  );
}

export function InventoryPage() {
  const overview = useInventoryOverview();
  const [view, setView] = useState<View>("movements");
  const [mutationMode, setMutationMode] = useState<"adjust" | "receive">();
  const { locale } = useInventoryLanguage();
  const adjustAction = <button type="button" className={styles.adjustButton} disabled={!overview.data?.materials.length} onClick={() => setMutationMode(view === "stock" ? "receive" : "adjust")}>{view === "stock" ? <PackagePlus aria-hidden="true" /> : <SlidersHorizontal aria-hidden="true" />}{locale === "en" ? (view === "stock" ? "Receive Stock" : "Adjust Inventory") : (view === "stock" ? "Terima Stok" : "Adjust Stok Gudang")}</button>;

  return (
    <InventoryShell title={locale === "en" ? "Inventory" : "Gudang"} actions={adjustAction}>
      <div className={styles.page}>
        {overview.isLoading && <LoadingState label={locale === "en" ? "Loading inventory data..." : "Memuat data gudang..."} />}
        {overview.isError && <ErrorState message={locale === "en" ? "Inventory data could not be loaded." : "Data gudang tidak dapat dimuat."} onRetry={() => void overview.refetch()} />}
        {mutationMode && overview.data && <StockMutationForm materials={overview.data.materials} mode={mutationMode} locale={locale} onClose={() => setMutationMode(undefined)} />}
        {overview.data && !overview.isError && <InventoryContent overview={overview.data} view={view} locale={locale} onViewChange={setView} />}
      </div>
    </InventoryShell>
  );
}
