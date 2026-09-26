import { forecastResponseSchema, productsResponseSchema, risksResponseSchema } from "@/domain/inventory-api";
import { inventoryRequest } from "@/lib/inventory-api";
export const getProducts = async () => (await inventoryRequest("/products", productsResponseSchema)).products;
export const getRisks = () => inventoryRequest("/inventory/risks", risksResponseSchema);
export const getForecast = (id: string) => inventoryRequest(`/forecasts/products/${encodeURIComponent(id)}?horizonDays=3`, forecastResponseSchema);
export async function allPages<T>(load: (page: number) => Promise<{ items: T[]; pagination: { totalPages: number } }>) {
  const first = await load(1);
  const items = [...first.items];
  for (let page = 2; page <= first.pagination.totalPages; page++) items.push(...(await load(page)).items);
  return items;
}
