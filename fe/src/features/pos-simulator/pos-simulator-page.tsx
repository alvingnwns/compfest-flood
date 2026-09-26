"use client";

import { Search } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { InventoryShell } from "@/components/layout/inventory-shell";
import { useInventoryLanguage, type InventoryLocale } from "@/components/providers/inventory-language-provider";
import { ErrorState, LoadingState, InventoryEmptyState } from "@/components/inventory/inventory-page-state";
import type { CheckoutResult, PosCatalogue, PosProduct } from "@/domain/pos-simulator";
import { usePosCatalogue, usePosCheckout } from "@/hooks/use-pos-simulator";
import { InventoryApiError } from "@/lib/inventory-api";
import { PosDialog, posProductName, type OrderLine, type PosDialogState } from "./pos-dialog";
import styles from "./pos-simulator.module.css";

const currency = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const materialNames: Record<string, { en: string; id: string }> = {
  Mangga: { en: "Mango", id: "Mangga" }, "Jeruk Peras": { en: "Orange", id: "Jeruk Peras" },
  Alpukat: { en: "Avocado", id: "Alpukat" }, Jambu: { en: "Guava", id: "Jambu" },
  Lemon: { en: "Lemon", id: "Lemon" }, Apel: { en: "Apple", id: "Apel" },
  Nanas: { en: "Pineapple", id: "Nanas" }, Pisang: { en: "Banana", id: "Pisang" },
};

function ProductCard({ product, locale, onAdd }: { product: PosProduct; locale: InventoryLocale; onAdd: () => void }) {
  return (
    <article className={styles.productCard}>
      <div className={styles.productVisual} style={{ backgroundColor: product.color }} />
      <div><h2>{posProductName(product, locale)}</h2>{product.materialName && product.materialUsageGrams !== undefined && <p>{locale === "en" ? "Usage" : "Pemakaian"}: {materialNames[product.materialName]?.[locale] ?? product.materialName} ({product.materialUsageGrams}g)</p>}</div>
      <strong>{currency.format(product.price)}</strong>
      <button type="button" onClick={onAdd}>{locale === "en" ? "Add +" : "Tambah +"}</button>
    </article>
  );
}

function OrderPanel({ lines, total, locale, onChange, onRemove, onClear, onCheckout }: { lines: OrderLine[]; total: number; locale: InventoryLocale; onChange: (id: string, delta: number) => void; onRemove: (id: string) => void; onClear: () => void; onCheckout: () => void }) {
  return (
    <aside className={styles.orderPanel} aria-labelledby="current-order-title">
      <h2 id="current-order-title">{locale === "en" ? "Current Order" : "Pesanan Saat Ini"}</h2>
      <div className={styles.basket}>
        {lines.map(({ product, quantity }) => <div className={styles.basketItem} key={product.id}>
          <div className={styles.itemRow}><strong>{posProductName(product, locale)}</strong><strong>{currency.format(product.price * quantity)}</strong></div>
          <div className={styles.adjustmentRow}><div className={styles.quantityControls}><button type="button" onClick={() => onChange(product.id, -1)} aria-label={`${locale === "en" ? "Decrease" : "Kurangi"} ${posProductName(product, locale)}`}>-</button><strong>{quantity}</strong><button type="button" onClick={() => onChange(product.id, 1)} aria-label={`${locale === "en" ? "Increase" : "Tambah"} ${posProductName(product, locale)}`}>+</button></div><button type="button" className={styles.removeButton} onClick={() => onRemove(product.id)}>{locale === "en" ? "Remove" : "Hapus"}</button></div>
        </div>)}
        {lines.length === 0 && <div className={styles.emptyBasket}>{locale === "en" ? "Your order is empty." : "Pesanan masih kosong."}</div>}
      </div>
      <div className={styles.orderFooter}>
        <div className={styles.subtotal}><span>Subtotal</span><strong>{currency.format(total)}</strong></div>
        <div className={styles.billing}><span>{locale === "en" ? "Total Billing" : "Total Tagihan"}</span><strong>{currency.format(total)}</strong></div>
        <button type="button" className={styles.checkoutButton} disabled={lines.length === 0} onClick={onCheckout}>{locale === "en" ? "Complete Transaction" : "Selesaikan Transaksi"}</button>
        <button type="button" className={styles.clearButton} disabled={lines.length === 0} onClick={onClear}>{locale === "en" ? "Clear Order" : "Kosongkan Pesanan"}</button>
      </div>
    </aside>
  );
}

function PosContent({ catalogue, locale }: { catalogue: PosCatalogue; locale: InventoryLocale }) {
  const [query, setQuery] = useState("");
  const [order, setOrder] = useState<Record<string, number>>(() => Object.fromEntries(catalogue.initialOrder.map((item) => [item.productId, item.quantity])));
  const [dialog, setDialog] = useState<PosDialogState>(null);
  const [result, setResult] = useState<CheckoutResult>();
  const [failure, setFailure] = useState<{ uncertain: boolean; message?: string }>();
  const checkout = usePosCheckout();
  const request = useRef<{ payload: string; key: string; items: { productId: string; quantity: number }[] } | null>(null);
  const busy = useRef(false);
  const products = useMemo(() => catalogue.products.filter((product) => posProductName(product, locale).toLowerCase().includes(query.trim().toLowerCase())), [catalogue.products, locale, query]);
  const lines = useMemo(() => catalogue.products.flatMap((product) => order[product.id] ? [{ product, quantity: order[product.id] }] : []), [catalogue.products, order]);
  const total = lines.reduce((sum, line) => sum + line.product.price * line.quantity, 0);
  const changeQuantity = (id: string, delta: number) => setOrder((current) => { const next = (current[id] ?? 0) + delta; if (next <= 0) { const { [id]: removed, ...rest } = current; void removed; return rest; } return { ...current, [id]: next }; });
  const clearOrder = () => setOrder({});
  const newOrder = () => { if (busy.current || failure?.uncertain) return; clearOrder(); setResult(undefined); setFailure(undefined); setDialog(null); checkout.reset(); request.current = null; };
  const confirm = async () => {
    if (busy.current) return;
    busy.current = true;
    const items = failure?.uncertain && request.current ? request.current.items : lines.map(({ product, quantity }) => ({ productId: product.id, quantity }));
    const payload = JSON.stringify(items);
    if (request.current?.payload !== payload) request.current = { payload, key: crypto.randomUUID(), items };
    try {
      const response = await checkout.mutateAsync({ items, idempotencyKey: request.current.key });
      setResult(response);
      setFailure(undefined);
      setDialog(response.status === "success" ? "success" : "shortage");
    } catch (error) {
      const definitive = error instanceof InventoryApiError && error.status >= 400 && error.status < 500 && ![408, 429].includes(error.status);
      setFailure({ uncertain: !definitive, message: definitive ? `${error.code}: ${error.message}` : undefined });
      setDialog("failed");
    } finally { busy.current = false; }
  };

  return (
    <>
      <fieldset className={styles.layout} disabled={checkout.isPending || failure?.uncertain} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
        <section className={styles.catalogue} aria-label={locale === "en" ? "Product catalogue" : "Katalog produk"}>
          <label className={styles.search}><Search aria-hidden="true" /><span className={styles.srOnly}>{locale === "en" ? "Search menu" : "Cari menu"}</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={locale === "en" ? "Search menu..." : "Cari menu..."} /></label>
          <div className={styles.productGrid}>{products.map((product) => <ProductCard key={product.id} product={product} locale={locale} onAdd={() => changeQuantity(product.id, 1)} />)}{products.length === 0 && <div className={styles.noProducts}>{locale === "en" ? "No menu items found." : "Menu tidak ditemukan."}</div>}</div>
        </section>
        <OrderPanel lines={lines} total={total} locale={locale} onChange={changeQuantity} onRemove={(id) => setOrder((current) => { const { [id]: removed, ...rest } = current; void removed; return rest; })} onClear={clearOrder} onCheckout={() => setDialog("confirmation")} />
      </fieldset>
      <PosDialog state={dialog} lines={lines} total={total} result={result} failure={failure} locale={locale} pending={checkout.isPending} onClose={() => { if (!busy.current && !failure?.uncertain) setDialog(null); }} onConfirm={() => void confirm()} onNewOrder={newOrder} />
    </>
  );
}

export function PosSimulatorPage() {
  const catalogue = usePosCatalogue();
  const { locale } = useInventoryLanguage();
  return <InventoryShell title="POS Simulator"><div className={styles.page}>{catalogue.isLoading && <LoadingState label={locale === "en" ? "Loading POS simulator..." : "Memuat simulator POS..."} />}{catalogue.isError && <ErrorState message={locale === "en" ? "POS catalogue could not be loaded." : "Katalog POS tidak dapat dimuat."} onRetry={() => void catalogue.refetch()} />}{catalogue.data && !catalogue.isError && (catalogue.data.products.length === 0 ? <InventoryEmptyState page="pos" locale={locale} /> : <PosContent catalogue={catalogue.data} locale={locale} />)}</div></InventoryShell>;
}
