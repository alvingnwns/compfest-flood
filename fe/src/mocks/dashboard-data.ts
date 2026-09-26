import type { DashboardSummary } from "@/domain/dashboard";

export const dashboardSummaryMock = {
  source: "mock",
  metrics: [
    { id: "gross-sales", label: "Penjualan Kotor", value: 2_450_000, format: "currency" },
    { id: "products-sold", label: "Produk Terjual", value: 37, format: "number" },
    { id: "at-risk-materials", label: "Bahan Berisiko", value: 2, format: "number" },
    { id: "pending-actions", label: "Tindakan Tertunda", value: 3, format: "number" },
  ],
  inventoryRisks: [
    { id: "ayam", materialName: "Ayam", availableQuantity: 2, predictedDemand: 6, unit: "kg", status: "out-of-stock", statusLabel: "Stok Habis", dueLabel: "Hari Ini" },
    { id: "tomat", materialName: "Tomat", availableQuantity: 4, predictedDemand: 6, unit: "kg", status: "low-stock", statusLabel: "Stok Sedikit", dueLabel: "Besok" },
    { id: "nasi", materialName: "Nasi", availableQuantity: 6, predictedDemand: 4, unit: "kg", status: "surplus", statusLabel: "Surplus", dueLabel: "2 Hari" },
  ],
  priorityRecommendations: [
    { id: "ayam", title: "Order 4 kg Ayam", detail: "Kebutuhan ayam untuk besok diperkirakan 6 kg. Stok ayam yang tersedia adalah 2 kg." },
    { id: "tomat", title: "Order 2 kg Tomat", detail: "Kebutuhan tomat untuk besok diperkirakan 6 kg. Stok tomat yang tersedia adalah 4 kg." },
  ],
  demandProjection: [
    { label: "H-3", actual: 38, predicted: null },
    { label: "H-2", actual: 46, predicted: null },
    { label: "H-1", actual: 43, predicted: null },
    { label: "Hari Ini", actual: 51, predicted: 51 },
    { label: "H+1", actual: null, predicted: 56 },
    { label: "H+2", actual: null, predicted: 62 },
    { label: "H+3", actual: null, predicted: 58 },
  ],
} satisfies DashboardSummary;
