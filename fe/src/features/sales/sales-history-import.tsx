"use client";

import { Download, FileUp, X } from "lucide-react";
import { useState } from "react";
import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import { salesHistoryRowErrorsSchema } from "@/domain/inventory-api";
import { useImportSalesHistory, useSalesHistoryCoverage } from "@/hooks/use-sales-history";
import { InventoryApiError } from "@/lib/inventory-api";
import { salesHistoryService } from "@/services/sales-history-service";
import styles from "./sales.module.css";

const errorMessages: Record<string, [en: string, id: string]> = {
  INVALID_SALES_HISTORY_COLUMNS: ["Required columns are missing. Use date, product_id (or product_name) and quantity.", "Kolom wajib tidak ditemukan. Gunakan date, product_id (atau product_name), dan quantity."],
  INVALID_SALES_HISTORY_ROWS: ["Some rows are invalid. Nothing was imported; fix the lines below and upload again.", "Ada baris yang tidak valid. Tidak ada data yang diimpor; perbaiki baris di bawah lalu unggah ulang."],
  SALES_HISTORY_OVERLAPS_POS: ["Some dates already have POS sales. Remove these dates from the file:", "Sebagian tanggal sudah memiliki transaksi POS. Hapus tanggal berikut dari file:"],
  SALES_HISTORY_TOO_LARGE: ["The file is too large (maximum 10 MB).", "Ukuran file terlalu besar (maksimal 10 MB)."],
  EMPTY_SALES_HISTORY: ["The file contains no sales rows.", "File tidak berisi data penjualan."],
  INVALID_SALES_HISTORY_ENCODING: ["Save the file as a UTF-8 CSV and try again.", "Simpan file sebagai CSV UTF-8 lalu coba lagi."],
};

function ImportError({ error, locale }: { error: Error; locale: InventoryLocale }) {
  const code = error instanceof InventoryApiError ? error.code : undefined;
  const message = code && errorMessages[code] ? errorMessages[code][locale === "en" ? 0 : 1] : error.message;
  const details = error instanceof InventoryApiError ? error.details : undefined;
  const rows = salesHistoryRowErrorsSchema.safeParse(details);
  const dates = code === "SALES_HISTORY_OVERLAPS_POS" && details && typeof details === "object" && "dates" in details && Array.isArray(details.dates) ? details.dates.map(String) : [];
  return (
    <div role="alert" className={styles.historyError}>
      <p>{message}</p>
      {rows.success && <ul>{rows.data.errors.slice(0, 10).map((row) => <li key={row.line}>{locale === "en" ? "Line" : "Baris"} {row.line}: {row.error}</li>)}</ul>}
      {dates.length > 0 && <p>{dates.join(", ")}</p>}
    </div>
  );
}

export function SalesHistoryImport({ locale, onClose }: { locale: InventoryLocale; onClose: () => void }) {
  const coverage = useSalesHistoryCoverage();
  const upload = useImportSalesHistory();
  const [file, setFile] = useState<File | null>(null);
  // One key per chosen file, so a retried upload of the same file is never applied twice.
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());
  const en = locale === "en";
  const status = coverage.data;

  return (
    <section className={styles.historyPanel} aria-labelledby="sales-history-title">
      <div className={styles.historyHeader}>
        <h2 id="sales-history-title">{en ? "Import Sales History" : "Impor Riwayat Penjualan"}</h2>
        <button type="button" onClick={onClose} aria-label={en ? "Close sales history import" : "Tutup impor riwayat penjualan"}><X /></button>
      </div>
      <p className={styles.historyIntro}>
        {en
          ? "Upload past daily sales so ARUNA can forecast with its model. Imported history never changes current stock."
          : "Unggah riwayat penjualan harian agar ARUNA dapat memprediksi dengan modelnya. Riwayat yang diimpor tidak mengubah stok saat ini."}
      </p>
      {status && (
        <p className={styles.historyCoverage} data-ready={status.ready}>
          {en ? "Recorded days for the model" : "Hari tercatat untuk model"}: <strong>{status.coveredDays}/{status.requiredDays}</strong>
          {" · "}
          {status.ready
            ? (en ? "Model forecast active" : "Prediksi model aktif")
            : (en ? `${status.requiredDays - status.coveredDays} more days needed` : `Butuh ${status.requiredDays - status.coveredDays} hari lagi`)}
        </p>
      )}
      <p className={styles.historyFormat}>
        {en
          ? "CSV columns: date (YYYY-MM-DD or DD/MM/YYYY), product_id or product_name, quantity. One row per product per day, or one row per transaction."
          : "Kolom CSV: date/tanggal (YYYY-MM-DD atau DD/MM/YYYY), product_id atau nama_produk, quantity/jumlah. Satu baris per produk per hari, atau per transaksi."}
        {" "}
        <a href={salesHistoryService.templateUrl} download><Download aria-hidden="true" />{en ? "Download template" : "Unduh template"}</a>
      </p>
      <form
        className={styles.historyForm}
        onSubmit={(event) => {
          event.preventDefault();
          if (file) upload.mutate({ file, idempotencyKey });
        }}
      >
        <label>
          <span className={styles.srOnly}>{en ? "Sales history CSV file" : "File CSV riwayat penjualan"}</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setIdempotencyKey(crypto.randomUUID());
              upload.reset();
            }}
          />
        </label>
        <button type="submit" className={styles.importButton} disabled={!file || upload.isPending}>
          <FileUp aria-hidden="true" />
          {upload.isPending ? (en ? "Uploading..." : "Mengunggah...") : (en ? "Upload" : "Unggah")}
        </button>
      </form>
      {upload.isError && <ImportError error={upload.error} locale={locale} />}
      {upload.data && (
        <p role="status" className={styles.historySuccess}>
          {en
            ? `Imported ${upload.data.daysImported} days (${upload.data.firstDate} to ${upload.data.lastDate}) for ${upload.data.productsImported} products.`
            : `Berhasil mengimpor ${upload.data.daysImported} hari (${upload.data.firstDate} s.d. ${upload.data.lastDate}) untuk ${upload.data.productsImported} produk.`}
          {upload.data.replacedDays > 0 && (en ? ` ${upload.data.replacedDays} existing days were replaced.` : ` ${upload.data.replacedDays} hari yang sudah ada diganti.`)}
        </p>
      )}
    </section>
  );
}
