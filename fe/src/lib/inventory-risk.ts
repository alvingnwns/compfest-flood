import type { ApiRiskLevel } from "@/domain/inventory-api";
import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
export const riskStatus = (level: ApiRiskLevel) => ({ LOW: "normal", MEDIUM: "low-stock", HIGH: "shortage-risk", STOCKOUT: "out-of-stock" } as const)[level];
export function inventoryStatusLabel(status: string, locale: InventoryLocale) {
  const labels: Record<string, [string, string]> = { normal: ["Safe", "Aman"], "low-stock": ["Low Stock", "Stok Menipis"], "shortage-risk": ["Shortage Risk", "Risiko Kekurangan"], "out-of-stock": ["Out of Stock", "Stok Habis"], surplus: ["Surplus", "Surplus"], expiring: ["Expiring", "Kedaluwarsa"] };
  return labels[status]?.[locale === "en" ? 0 : 1] ?? status;
}
