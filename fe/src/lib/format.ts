import type { RiskLevel } from "@/domain/common";

const idr = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const date = new Intl.DateTimeFormat("id-ID", { day: "2-digit", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });

export const formatIdr = (value: number) => idr.format(value).replace("Rp", "Rp ");
export const formatCompactIdr = (value: number) => value >= 1_000_000 ? `Rp ${(value / 1_000_000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt` : formatIdr(value);
export const formatPercent = (value: number) => `${Math.round(value * 100)}%`;
export const formatMinutes = (value: number) => {
  const rounded = Math.round(value * 10) / 10;
  return rounded >= 60 ? `${Math.floor(rounded / 60)}j ${Math.round(rounded % 60)}m` : `${rounded}m`;
};
export const formatDate = (value: string) => date.format(new Date(`${value}T00:00:00+07:00`));
export const formatRisk = (value: RiskLevel) => ({ low: "Rendah", medium: "Sedang", high: "Tinggi", critical: "Kritis" })[value];
export const formatDataMode = (value: string) => ({ historical_snapshot: "Rekaman historis", live: "Langsung", hybrid: "Hibrida" } as Record<string, string>)[value] ?? value;
export const formatHistoricalStatus = (value: string) => ({ available: "Tersedia", offline_snapshot: "Rekaman luring", unavailable: "Tidak tersedia" } as Record<string, string>)[value] ?? value;
export const formatAction = (value: string) => ({ allocate: "Alokasikan pesanan", reallocate: "Alihkan gudang", reroute: "Ubah rute", "reallocate-reroute": "Alihkan + ubah rute", substitute: "Substitusi", "split-substitute": "Bagi + substitusi" } as Record<string, string>)[value] ?? value;
