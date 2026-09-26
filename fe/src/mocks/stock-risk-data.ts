import type { StockRiskOverview } from "@/domain/stock-risk";

export const stockRiskOverviewMock: StockRiskOverview = {
  source: "mock",
  businessDate: "2026-09-27",
  materials: [
    { id: "mat-mangga", name: "Mangga", currentStock: 2, predictedNeed: 6, unit: "kg", difference: -4, status: "out-of-stock", restockLeadTime: "1 Hari Kerja" },
    { id: "mat-alpukat", name: "Alpukat", currentStock: 25, predictedNeed: 3, unit: "kg", difference: 22, status: "surplus", restockLeadTime: "7 Hari Kerja" },
    { id: "mat-jeruk-nipis", name: "Jeruk Nipis", currentStock: 3, predictedNeed: 4.5, unit: "kg", difference: -1.5, status: "low-stock", restockLeadTime: "2 Hari Kerja" },
    { id: "mat-nanas", name: "Nanas", currentStock: 1, predictedNeed: 3, unit: "kg", difference: -2, status: "out-of-stock", restockLeadTime: "1 Hari Kerja" },
    { id: "mat-kiwi", name: "Kiwi", currentStock: 7, predictedNeed: 5, unit: "kg", difference: 2, status: "normal", restockLeadTime: "5 Hari Kerja" },
  ],
};
