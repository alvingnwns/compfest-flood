import type { DemandForecast } from "@/domain/demand-forecast";

export const demandForecastMock = {
  source: "mock",
  productId: "jus-mangga",
  productName: "Jus Mangga",
  horizonDays: 3,
  totalPredictedSales: 105,
  points: [
    { label: "H-3", actual: 38, predicted: null },
    { label: "H-2", actual: 43, predicted: null },
    { label: "H-1", actual: 40, predicted: null },
    { label: "Hari Ini", actual: 55, predicted: 55 },
    { label: "H+1", actual: null, predicted: 50 },
    { label: "H+2", actual: null, predicted: 63 },
    { label: "H+3", actual: null, predicted: 63 },
  ],
  details: [
    { dateLabel: "28 Sep (H+1)", productName: "Jus Mangga", predictedSales: 15, primaryMaterial: "Mangga", estimatedRequirement: 3, unit: "kg" },
    { dateLabel: "29 Sep (H+2)", productName: "Jus Mangga", predictedSales: 18, primaryMaterial: "Mangga", estimatedRequirement: 3.6, unit: "kg" },
    { dateLabel: "30 Sep (H+3)", productName: "Jus Mangga", predictedSales: 22, primaryMaterial: "Mangga", estimatedRequirement: 4.4, unit: "kg" },
  ],
} satisfies DemandForecast;
