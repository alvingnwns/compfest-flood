import { demandForecastSchema } from "@/domain/demand-forecast";
import { demandForecastMock } from "@/mocks/demand-forecast-data";
import { usesInventoryApi } from "@/lib/inventory-api";
import { getForecast, getProducts } from "./inventory-api-data";

export const demandForecastService = {
  getForecast: async (productId?: string) => {
    if (!usesInventoryApi()) return demandForecastSchema.parse(demandForecastMock);
    const products = await getProducts();
    if (products.length === 0) {
      return demandForecastSchema.parse({
        source: "api", productId: "", productName: "", horizonDays: 3,
        totalPredictedSales: 0, products: [], points: [], details: [], requirements: [],
      });
    }
    const id = productId ?? products[0]?.id;
    if (!id) throw new Error("No active products are available.");
    const forecast = await getForecast(id);
    return demandForecastSchema.parse({
      source: "api", productId: id, productName: forecast.product.name, horizonDays: forecast.horizonDays,
      products: products.map(({ id, name }) => ({ id, name })),
      totalPredictedSales: forecast.forecast.reduce((sum, item) => sum + item.predictedDemand, 0),
      points: [
        ...forecast.history.slice(-3).map((point) => ({ label: point.date, actual: point.actualDemand, predicted: null, historySource: point.historySource })),
        ...forecast.forecast.map((point) => ({ label: point.date, actual: null, predicted: point.predictedDemand })),
      ],
      details: forecast.forecast.map((point) => ({ dateLabel: point.date, productName: forecast.product.name, predictedSales: point.predictedDemand })),
      requirements: forecast.ingredientRequirements.map((item) => ({ name: item.ingredientName, quantity: item.totalRequired, unit: item.unit })),
      modelLabel: `${forecast.model.name} · ${forecast.model.version}`,
      synthetic: forecast.isSynthetic ?? false,
      forecastSource: forecast.source,
      trainingDataSynthetic: forecast.trainingDataSynthetic,
      fallbackReason: forecast.fallbackReason,
    });
  },
};
