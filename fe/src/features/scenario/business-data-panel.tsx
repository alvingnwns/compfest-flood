"use client";

import { BarChart3, CheckCircle2, Download, FileSpreadsheet, Upload } from "lucide-react";
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
    onModeChange("custom");
    onUpload(file);
  };

  return (
    <section aria-labelledby="business-data-title" className="mx-auto w-full max-w-[700px] text-center">
      <fieldset className="sr-only">
        <legend>Sumber Business Data</legend>
        <label><input type="radio" name="business-data-mode" checked={mode === "demo"} onChange={() => onModeChange("demo")} /> Demo Business Data</label>
        <label><input type="radio" name="business-data-mode" checked={mode === "custom"} onChange={() => onModeChange("custom")} /> Custom Business Data</label>
      </fieldset>

      <h2 id="business-data-title" className="text-[20px] font-bold text-primary-dark md:text-[24px]">SNAPSHOT BISNIS</h2>
      <p className="mt-1 text-[14px] font-medium text-primary-dark md:text-[16px]">Unggah snapshot operasional bisnis Anda</p>
      <p className="sr-only">Business Data: {mode === "custom" && activeSnapshotId ? "Custom Upload" : "Demo"}</p>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
        <a href={businessDataService.templateUrl} download className="inline-flex h-10 items-center gap-2 rounded-[10px] border border-primary/50 bg-white px-4 text-[13px] font-bold text-primary transition hover:bg-surface-low hover:ring-[2px] hover:ring-primary hover:ring-offset-2 focus-visible:ring-[2px] focus-visible:ring-primary focus-visible:ring-offset-2">
          <Download className="h-4 w-4" /> Download Excel Template
        </a>
        <button
          type="button"
          disabled={pending || disabled}
          onClick={() => {
            onModeChange("custom");
            inputRef.current?.click();
          }}
          className={`inline-flex h-10 items-center gap-2 rounded-[10px] bg-primary px-4 text-[13px] font-bold text-white transition hover:bg-primary-dark hover:ring-[2px] hover:ring-primary hover:ring-offset-2 focus-visible:ring-[2px] focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:hover:ring-0 ${
            mode === "custom" ? "ring-[2px] ring-primary ring-offset-2 shadow-sm" : ""
          }`}
        >
          <Upload className="h-4 w-4" /> {pending ? "Memvalidasi..." : "Upload Business Data"}
        </button>
        <input ref={inputRef} type="file" className="sr-only" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" aria-label="Upload Business Data" onChange={(event) => selectFile(event.target.files?.[0])} />
      </div>

      <p className="my-2.5 text-[15px] font-semibold text-primary-dark">atau</p>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onModeChange("demo")}
        className={`inline-flex h-10 items-center gap-2 rounded-[10px] border border-[#856019] bg-gradient-to-br from-[#eba92d] to-[#856019] px-4 text-[13px] font-bold text-white transition hover:brightness-105 hover:ring-[2px] hover:ring-[#eba92d] hover:ring-offset-2 focus-visible:ring-[2px] focus-visible:ring-[#eba92d] focus-visible:ring-offset-2 disabled:opacity-50 disabled:hover:ring-0 ${
          mode === "demo" ? "ring-[2px] ring-[#eba92d] ring-offset-2 shadow-sm" : ""
        }`}
      >
        <BarChart3 className="h-4 w-4" /> Gunakan Demo Data Bisnis
      </button>

      {(localError || error) && (
        <div className="mx-auto mt-5 max-w-xl rounded-lg border border-danger/30 bg-danger-soft/70 p-3 text-left text-xs text-danger" role="alert">
          <p className="font-semibold">{localError || error?.message}</p>
          {issues?.success && issues.data.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
              {issues.data.slice(0, 8).map((issue, index) => <li key={`${issue.sheet}-${issue.row}-${issue.code}-${index}`}>{issue.message}</li>)}
            </ul>
          )}
        </div>
      )}

      {mode === "custom" && !preview && !error && (
        <p className="mt-4 text-xs text-muted">Data operasional pengguna berjalan pada jaringan logistik demo Jakarta ResiliChain.</p>
      )}

      {mode === "custom" && preview && (
        <div className="mx-auto mt-5 max-w-2xl rounded-[20px] bg-white p-4 text-left shadow-[0_0_7px_rgb(0_0_0/20%)]">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
            <CheckCircle2 size={18} className="text-success" /> Data tervalidasi
          </div>
          <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
            <Metric label="Produk" value={preview.summary.productsLoaded} />
            <Metric label="Pesanan" value={preview.summary.ordersLoaded} />
            <Metric label="Inventori" value={preview.summary.inventoryRows} />
            <Metric label="Material" value={preview.summary.materialsLoaded} />
            <Metric label="Relasi BOM" value={preview.summary.bomRelationships} />
            <Metric label="Nilai Pesanan" value={formatIdr(preview.summary.totalOrderValue)} />
          </dl>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1.5 text-xs text-muted"><FileSpreadsheet size={14} /> Snapshot tersimpan sementara.</span>
            <button type="button" disabled={Boolean(activeSnapshotId) || disabled} onClick={onConfirm} className="rounded-[10px] bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark disabled:opacity-60">
              {activeSnapshotId ? "Data Aktif" : "Gunakan Data"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div><dt className="text-muted">{label}</dt><dd className="mt-0.5 font-semibold text-ink">{value}</dd></div>;
}
