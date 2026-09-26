"use client";
import { useEffect, useRef, useState } from "react";
import type { MaterialStock } from "@/domain/inventory";
import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import { useReceivingSuppliers, useStockMutation } from "@/hooks/use-inventory-overview";
import { InventoryApiError } from "@/lib/inventory-api";
import styles from "./stock-mutation-form.module.css";

type Ingredient = Pick<MaterialStock, "id" | "name" | "quantity" | "unit" | "inventoryVersion">;
export function StockMutationForm({ materials, mode, locale, onClose, supplierId, recommendationId, suggestedQuantity }: { materials: Ingredient[]; mode: "adjust" | "receive"; locale: InventoryLocale; onClose: () => void; supplierId?: string; recommendationId?: string; suggestedQuantity?: number }) {
  const [id, setId] = useState(materials[0]?.id ?? "");
  const material = materials.find((item) => item.id === id);
  const [quantity, setQuantity] = useState(String(suggestedQuantity ?? (mode === "adjust" ? materials[0]?.quantity ?? 0 : "")));
  const [supplier, setSupplier] = useState(supplierId ?? "");
  const [reason, setReason] = useState("PHYSICAL_COUNT");
  const [note, setNote] = useState("");
  const [receipt, setReceipt] = useState("");
  const [success, setSuccess] = useState(false);
  const [validation, setValidation] = useState("");
  const [expectedVersion, setExpectedVersion] = useState(materials[0]?.inventoryVersion);
  const [stale, setStale] = useState(false);
  const mutation = useStockMutation();
  const suppliers = useReceivingSuppliers(mode === "receive" && !supplierId);
  const request = useRef<{ payload: string; key: string } | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const busy = useRef(false);
  const generatedReceipt = useRef(crypto.randomUUID());
  useEffect(() => { dialog.current?.showModal(); }, []);
  const title = mode === "adjust" ? (locale === "en" ? "Adjust Stock" : "Sesuaikan Stok") : (locale === "en" ? "Receive Stock" : "Terima Stok");
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!material || busy.current || success || stale || (mode === "adjust" && expectedVersion === undefined)) return;
    const value = Number(quantity);
    if (quantity.trim() === "" || !Number.isFinite(value) || value < 0 || (mode === "receive" && value <= 0)) { setValidation(locale === "en" ? "Enter a valid quantity." : "Masukkan jumlah yang valid."); return; }
    const payload = mode === "adjust" ? { countedStock: value, unit: material.unit, reason, note: note || null, expectedInventoryVersion: expectedVersion } : { quantity: value, unit: material.unit, supplierId: supplier.trim(), note: note || null, recommendationId, externalReceiptId: receipt.trim() || generatedReceipt.current };
    const serialized = JSON.stringify({ id, payload });
    if (request.current?.payload !== serialized) request.current = { payload: serialized, key: crypto.randomUUID() };
    busy.current = true; setValidation("");
    try { await mutation.mutateAsync({ id, mode, payload, key: request.current.key }); setSuccess(true); } catch (error) { if (error instanceof InventoryApiError && error.code === "STALE_INVENTORY") setStale(true); } finally { busy.current = false; }
  };
  return <dialog ref={dialog} className={styles.dialog} onCancel={(event) => { event.preventDefault(); if (!mutation.isPending) onClose(); }} aria-labelledby="stock-mutation-title">
    <form onSubmit={(event) => void submit(event)}>
      <h2 id="stock-mutation-title">{title}</h2>
      {success ? <p role="status">{locale === "en" ? "Stock updated successfully." : "Stok berhasil diperbarui."}</p> : <>
        <label>{locale === "en" ? "Material" : "Bahan"}<select value={id} disabled={!!recommendationId || mutation.isPending || stale} onChange={(event) => { setId(event.target.value); if (mode === "adjust") { const selected = materials.find((item) => item.id === event.target.value); setQuantity(String(selected?.quantity ?? 0)); setExpectedVersion(selected?.inventoryVersion); } }}>{materials.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label>{mode === "adjust" ? (locale === "en" ? "Physical stock count" : "Jumlah stok fisik") : (locale === "en" ? "Quantity received" : "Jumlah diterima")} ({material?.unit})<input type="number" required min={mode === "adjust" ? 0 : 0.000001} step={material?.unit === "pcs" ? "1" : "any"} value={quantity} disabled={mutation.isPending} onChange={(event) => setQuantity(event.target.value)} /></label>
        {mode === "adjust" ? <label>{locale === "en" ? "Reason" : "Alasan"}<select value={reason} onChange={(event) => setReason(event.target.value)}><option value="PHYSICAL_COUNT">{locale === "en" ? "Physical Count" : "Hitung Fisik"}</option><option value="WASTE">{locale === "en" ? "Waste" : "Terbuang"}</option><option value="DAMAGE">{locale === "en" ? "Damage" : "Rusak"}</option><option value="OTHER">{locale === "en" ? "Other" : "Lainnya"}</option></select></label> : <>
          <label>{locale === "en" ? "Supplier" : "Pemasok"}{supplierId ? <input readOnly value={supplierId} /> : suppliers.data?.length ? <select required value={supplier} onChange={(event) => setSupplier(event.target.value)}><option value="">{locale === "en" ? "Select supplier" : "Pilih pemasok"}</option>{suppliers.data.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select> : <input required placeholder={locale === "en" ? "Supplier ID" : "ID Pemasok"} value={supplier} onChange={(event) => setSupplier(event.target.value)} />}</label>
          <label>{locale === "en" ? "Receipt reference (optional)" : "Referensi penerimaan (opsional)"}<input value={receipt} onChange={(event) => setReceipt(event.target.value)} /></label>
          <p>{locale === "en" ? "Confirm only stock that has physically arrived." : "Konfirmasi hanya stok yang sudah diterima secara fisik."}</p>
        </>}
        <label>{locale === "en" ? "Note (optional)" : "Catatan (opsional)"}<textarea maxLength={500} value={note} onChange={(event) => setNote(event.target.value)} /></label>
        {mode === "adjust" && expectedVersion === undefined && <p role="alert">{locale === "en" ? "Inventory version unavailable. Refresh inventory before counting." : "Versi stok tidak tersedia. Muat ulang stok sebelum menghitung."}</p>}
        {stale ? <p role="alert">{locale === "en" ? "Stock changed while you were counting. Inventory has been refreshed. Close this form and recount before submitting a new adjustment." : "Stok berubah saat penghitungan. Data sudah dimuat ulang. Tutup form lalu hitung ulang sebelum penyesuaian baru."}</p> : (validation || mutation.error) && <p role="alert">{validation || mutation.error?.message}</p>}
      </>}
      <div className={styles.actions}><button type="button" disabled={mutation.isPending} onClick={onClose}>{success ? (locale === "en" ? "Done" : "Selesai") : stale ? (locale === "en" ? "Close and recount" : "Tutup dan hitung ulang") : (locale === "en" ? "Cancel" : "Batal")}</button>{!success && <button disabled={mutation.isPending || !material || stale || (mode === "adjust" && expectedVersion === undefined)}>{mutation.isPending ? (locale === "en" ? "Saving..." : "Menyimpan...") : title}</button>}</div>
    </form>
  </dialog>;
}
