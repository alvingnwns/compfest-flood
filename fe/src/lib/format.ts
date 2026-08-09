import type { RiskLevel } from "@/domain/common";

const idr = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });
const date = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "long", year: "numeric", timeZone: "Asia/Jakarta" });

export const formatIdr = (value: number) => idr.format(value).replace("Rp", "Rp ");
export const formatCompactIdr = (value: number) => value >= 1_000_000 ? `Rp ${(value / 1_000_000).toLocaleString("id-ID", { maximumFractionDigits: 1 })} jt` : formatIdr(value);
export const formatPercent = (value: number) => `${Math.round(value * 100)}%`;
export const formatMinutes = (value: number) => value >= 60 ? `${Math.floor(value / 60)}j ${value % 60}m` : `${value}m`;
export const formatDate = (value: string) => date.format(new Date(`${value}T00:00:00+07:00`));
export const formatRisk = (value: RiskLevel) => ({ low: "Low", medium: "Medium", high: "High", critical: "Critical" })[value];
