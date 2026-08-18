"use client";

import { CheckCircle2, Download, FileSpreadsheet, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { importValidationIssueSchema, type BusinessImportResponse } from "@/domain/business-data";
import { ApiError } from "@/lib/api-client";
import { formatIdr } from "@/lib/format";
import { businessDataService } from "@/services/business-data-service";

type Props = {
  mode: "demo" | "custom";
  preview?: BusinessImportResponse;
  activeSnapshotId?: string;
  pending: boolean;
  error?: Error | null;
  disabled?: boolean;
  onModeChange: (mode: "demo" | "custom") => void;
  onUpload: (file: File) => void;
  onConfirm: () => void;
};

export function BusinessDataPanel({
  mode,
  preview,
  activeSnapshotId,
  pending,
  error,
  disabled,
  onModeChange,
  onUpload,
  onConfirm,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [localError, setLocalError] = useState("");
  const issues = error instanceof ApiError
    ? importValidationIssueSchema.array().safeParse(error.details?.errors)
    : undefined;

  const selectFile = (file?: File) => {
    setLocalError("");
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      setLocalError("Gunakan workbook Excel tanpa macro dengan format .xlsx.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setLocalError("Ukuran workbook melebihi batas 5 MB.");
      return;
    }
    onUpload(file);
  };

  return (
    <section className="card mb-6 p-5" aria-labelledby="business-data-title">
      <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
        <div>
          <div className="eyebrow mb-1">Business Data</div>
          <h2 id="business-data-title" className="section-title">Snapshot Bisnis</h2>
          <p className="mt-1 text-xs text-muted">Pilih data demo atau unggah snapshot operasional Anda.</p>
        </div>
        <span className="rounded-full border border-outline bg-surface-low px-2.5 py-1 text-[11px] font-semibold text-muted">
          Business Data: {mode === "custom" && activeSnapshotId ? "Custom Upload" : "Demo"}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className={`rounded-lg border p-3 ${mode === "demo" ? "border-primary bg-primary/5" : "border-outline"}`}>
          <span className="flex items-center gap-2 text-sm font-semibold text-ink">
            <input type="radio" name="business-data-mode" checked={mode === "demo"} disabled={disabled} onChange={() => onModeChange("demo")} />
            Demo Business Data
          </span>
          <span className="mt-1 block pl-6 text-xs text-muted">Menggunakan snapshot perusahaan demo bawaan ResiliChain.</span>
        </label>
        <label className={`rounded-lg border p-3 ${mode === "custom" ? "border-primary bg-primary/5" : "border-outline"}`}>
          <span className="flex items-center gap-2 text-sm font-semibold text-ink">
            <input type="radio" name="business-data-mode" checked={mode === "custom"} disabled={disabled} onChange={() => onModeChange("custom")} />
            Custom Business Data
          </span>
          <span className="mt-1 block pl-6 text-xs text-muted">Produk, harga, pesanan, inventori, material, dan BOM dari workbook Anda.</span>
        </label>
      </div>

      {mode === "custom" && (
        <div className="mt-4 rounded-lg border border-outline bg-surface-low p-4">
          <p className="mb-3 text-xs text-muted">
            Data operasional pengguna berjalan pada jaringan logistik demo Jakarta ResiliChain. Fasilitas, kendaraan, dan geografi tetap data demo.
          </p>
          <div className="flex flex-wrap gap-2">
            <a href={businessDataService.templateUrl} download className="inline-flex items-center gap-2 rounded-lg border border-outline bg-surface px-3 py-2 text-sm font-medium text-ink hover:bg-surface-high">
              <Download size={16} /> Download Excel Template
            </a>
            <button type="button" disabled={pending || disabled} onClick={() => inputRef.current?.click()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-50">
              <Upload size={16} /> {pending ? "Memvalidasi…" : "Upload Business Data"}
            </button>
            <input ref={inputRef} type="file" className="sr-only" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" aria-label="Upload Business Data" onChange={(event) => selectFile(event.target.files?.[0])} />
          </div>

          {(localError || error) && (
            <div className="mt-3 rounded-lg border border-danger/30 bg-danger/5 p-3 text-xs text-danger" role="alert">
              <p className="font-semibold">{localError || error?.message}</p>
              {issues?.success && issues.data.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
                  {issues.data.slice(0, 8).map((issue, index) => <li key={`${issue.sheet}-${issue.row}-${issue.code}-${index}`}>{issue.message}</li>)}
                </ul>
              )}
            </div>
          )}

          {preview && (
            <div className="mt-4 rounded-lg border border-primary/25 bg-surface p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
                <CheckCircle2 size={18} className="text-success" /> Data tervalidasi
              </div>
              <dl className="grid grid-cols-2 gap-x-5 gap-y-2 text-xs sm:grid-cols-3 lg:grid-cols-6">
                <Metric label="Produk" value={preview.summary.productsLoaded} />
                <Metric label="Pesanan" value={preview.summary.ordersLoaded} />
                <Metric label="Inventori" value={preview.summary.inventoryRows} />
                <Metric label="Material" value={preview.summary.materialsLoaded} />
                <Metric label="Relasi BOM" value={preview.summary.bomRelationships} />
                <Metric label="Nilai Pesanan" value={formatIdr(preview.summary.totalOrderValue)} />
              </dl>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 text-xs text-muted"><FileSpreadsheet size={14} /> Snapshot tersimpan sementara hingga sesi backend berakhir atau kedaluwarsa.</span>
                <button type="button" disabled={Boolean(activeSnapshotId) || disabled} onClick={onConfirm} className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60">
                  {activeSnapshotId ? "Data Aktif" : "Gunakan Data"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div><dt className="text-muted">{label}</dt><dd className="mt-0.5 font-semibold text-ink">{value}</dd></div>;
}
