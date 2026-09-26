import { AlertTriangle, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import type { CheckoutResult, PosProduct } from "@/domain/pos-simulator";
import { localizeInventoryTerm } from "@/lib/inventory-translations";
import styles from "./pos-simulator.module.css";

export type PosDialogState = "confirmation" | "success" | "failed" | "shortage" | null;
export type OrderLine = { product: PosProduct; quantity: number };

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const productNames: Record<string, { en: string; id: string }> = {
  mango: { en: "Mango Juice", id: "Jus Mangga" },
  orange: { en: "Orange Juice", id: "Jus Jeruk" },
  avocado: { en: "Avocado Juice", id: "Jus Alpukat" },
  guava: { en: "Guava Juice", id: "Jus Jambu" },
  lemonade: { en: "Lemonade", id: "Limun" },
  apple: { en: "Apple Juice", id: "Jus Apel" },
  pineapple: { en: "Pineapple Juice", id: "Jus Nanas" },
  banana: { en: "Banana Juice", id: "Jus Pisang" },
};

export const posProductName = (product: PosProduct, locale: InventoryLocale) => productNames[product.id]?.[locale] ?? localizeInventoryTerm(product.name, locale);

function Receipt({ lines, total, locale }: { lines: OrderLine[]; total: number; locale: InventoryLocale }) {
  return (
    <div className={styles.receiptBox}>
      <div className={styles.receiptHeader}><strong>{locale === "en" ? "Items sold" : "Item terjual"}</strong><strong>Subtotal</strong></div>
      {lines.map(({ product, quantity }) => <div className={styles.receiptLine} key={product.id}><span>{quantity}x {posProductName(product, locale)}</span><span>{currency.format(product.price * quantity)}</span></div>)}
      <div className={styles.receiptRule} />
      <div className={styles.receiptTotal}><strong>Total</strong><strong>{currency.format(total)}</strong></div>
    </div>
  );
}

function StandardDialog({ state, lines, total, transactionId, locale, pending, onClose, onConfirm, onNewOrder }: { state: Exclude<PosDialogState, "shortage" | "failed" | null>; lines: OrderLine[]; total: number; transactionId?: string; locale: InventoryLocale; pending: boolean; onClose: () => void; onConfirm: () => void; onNewOrder: () => void }) {
  const success = state === "success";
  return (
    <div className={styles.modalCard} role="dialog" aria-modal="true" aria-labelledby="pos-dialog-title">
      <div className={styles.iconBanner}><span className={styles.iconCircle}><Image src={success ? "/pos-check.svg" : "/pos-receipt.svg"} alt="" width={32} height={32} /></span></div>
      <div className={styles.modalContent}>
        <div className={styles.modalTitle}>
          <h2 id="pos-dialog-title">{success ? (locale === "en" ? "Transaction Completed" : "Transaksi Selesai") : (locale === "en" ? "Confirm Order" : "Konfirmasi Pesanan")}</h2>
          <p>{success ? `${locale === "en" ? "Transaction ID" : "ID Transaksi"}: ${transactionId}` : (locale === "en" ? "Make sure your order is correct" : "Pastikan pesanan sudah benar")}</p>
        </div>
        <Receipt lines={lines} total={total} locale={locale} />
      </div>
      <div className={styles.modalFooter}>
        {success ? <button type="button" className={styles.newOrderButton} onClick={onNewOrder}>{locale === "en" ? "New Order" : "Pesanan Baru"}</button> : <div className={styles.confirmButtons}><button type="button" className={styles.cancelButton} disabled={pending} onClick={onClose}>{locale === "en" ? "Cancel" : "Batal"}</button><button type="button" className={styles.confirmButton} disabled={pending} onClick={onConfirm}>{pending ? (locale === "en" ? "Processing..." : "Memproses...") : (locale === "en" ? "Confirm" : "Konfirmasi")}</button></div>}
      </div>
    </div>
  );
}

function ShortageDialog({ result, locale, onClose }: { result: Extract<CheckoutResult, { status: "insufficient-stock" }>; locale: InventoryLocale; onClose: () => void }) {
  return (
    <div className={`${styles.modalCard} ${styles.warningModal}`} role="dialog" aria-modal="true" aria-labelledby="shortage-title">
      <div className={styles.warningContent}>
        <h2 id="shortage-title"><AlertTriangle aria-hidden="true" />{locale === "en" ? "Insufficient Stock" : "Stok Tidak Mencukupi"}</h2>
        <p>{locale === "en" ? "Cannot complete this transaction. The following ingredient does not have enough stock:" : "Transaksi tidak dapat diselesaikan. Bahan berikut tidak memiliki stok yang cukup:"}</p>
        <div className={styles.shortageTableWrap}><table><thead><tr><th>{locale === "en" ? "Ingredient" : "Bahan"}</th><th>{locale === "en" ? "Required" : "Dibutuhkan"}</th><th>{locale === "en" ? "Available" : "Tersedia"}</th><th>{locale === "en" ? "Shortage" : "Kekurangan"}</th></tr></thead><tbody>{result.shortages.map((item) => <tr key={item.materialName}><td>{localizeInventoryTerm(item.materialName, locale)}</td><td>{item.unit ? `${item.required} ${item.unit}` : `${item.requiredGrams}g (${((item.requiredGrams ?? 0) / 1000).toFixed(1)} kg)`}</td><td>{item.unit ? `${item.available} ${item.unit}` : `${item.availableGrams}g (${((item.availableGrams ?? 0) / 1000).toFixed(1)} kg)`}</td><td>{item.unit ? `${item.shortage} ${item.unit}` : `${item.shortageGrams}g (${((item.shortageGrams ?? 0) / 1000).toFixed(1)} kg)`}</td></tr>)}</tbody></table></div>
        <p className={styles.warningHint}>{locale === "en" ? "Reduce the order quantity or receive more stock before completing this transaction." : "Kurangi jumlah pesanan atau tambah stok sebelum menyelesaikan transaksi ini."}</p>
      </div>
      <div className={styles.warningFooter}><Link href="/gudang">{locale === "en" ? "Go to Inventory" : "Ke Gudang"}</Link><button type="button" onClick={onClose}>{locale === "en" ? "Back to Order" : "Kembali ke Pesanan"}</button></div>
    </div>
  );
}

export function PosDialog({ state, lines, total, result, failure, locale, pending = false, onClose, onConfirm, onNewOrder }: { state: PosDialogState; lines: OrderLine[]; total: number; result?: CheckoutResult; failure?: { uncertain: boolean; message?: string }; locale: InventoryLocale; pending?: boolean; onClose: () => void; onConfirm: () => void; onNewOrder: () => void }) {
  if (!state) return null;
  return <div className={styles.modalOverlay} onMouseDown={(event) => { if (event.target === event.currentTarget && state === "confirmation" && !pending) onClose(); }}>
    {state === "shortage" && result?.status === "insufficient-stock" ? <ShortageDialog result={result} locale={locale} onClose={onClose} /> : state === "failed" ? <div className={`${styles.modalCard} ${styles.failedModal}`} role="dialog" aria-modal="true"><div className={styles.failedBanner}><span><X /></span></div><div className={styles.failedContent}><h2>{failure?.uncertain ? (locale === "en" ? "Transaction status unknown" : "Status transaksi belum diketahui") : (locale === "en" ? "Transaction Failed" : "Transaksi Gagal")}</h2><p>{failure?.uncertain ? (locale === "en" ? "The server may have completed this order. Keep this page open and retry the same order to recover its result safely." : "Server mungkin sudah menyelesaikan pesanan. Tetap di halaman ini dan ulangi pesanan yang sama untuk memperoleh hasilnya dengan aman.") : failure?.message ?? (locale === "en" ? "Please try again" : "Silakan coba lagi")}</p></div><div className={styles.modalFooter}><button type="button" className={styles.newOrderButton} disabled={pending} onClick={failure?.uncertain ? onConfirm : onClose}>{pending ? (locale === "en" ? "Processing..." : "Memproses...") : failure?.uncertain ? (locale === "en" ? "Retry same order" : "Ulangi pesanan yang sama") : (locale === "en" ? "Back to Order" : "Kembali ke Pesanan")}</button></div></div> : <StandardDialog state={state as "confirmation" | "success"} lines={lines} total={total} transactionId={result?.status === "success" ? result.transactionId : undefined} locale={locale} pending={pending} onClose={onClose} onConfirm={onConfirm} onNewOrder={onNewOrder} />}
  </div>;
}
