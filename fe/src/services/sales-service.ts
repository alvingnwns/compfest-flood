import { salesOverviewSchema, salesTransactionSchema } from "@/domain/sales";
import { transactionResponseSchema, transactionsResponseSchema } from "@/domain/inventory-api";
import { salesOverviewMock } from "@/mocks/sales-data";
import { inventoryRequest, usesInventoryApi, wibDate } from "@/lib/inventory-api";
import { allPages } from "./inventory-api-data";

export const salesService = {
  getOverview: async () => {
    if (!usesInventoryApi()) return salesOverviewSchema.parse(salesOverviewMock);
    const date = wibDate();
    const transactions = await allPages((page) => inventoryRequest(`/transactions?date=${date}&pageSize=100&page=${page}`, transactionsResponseSchema));
    return salesOverviewSchema.parse({
      source: "api", businessDate: date,
      summary: { revenue: transactions.reduce((sum, item) => sum + item.totalAmount, 0), transactionCount: transactions.length, cupsSold: transactions.reduce((sum, item) => sum + item.totalItems, 0) },
      transactions: transactions.map((item) => ({ id: item.id, occurredAt: item.createdAt, cupCount: item.totalItems, total: item.totalAmount, items: [], inventoryDeductions: [] })),
    });
  },
  getTransaction: async (id: string) => {
    if (!usesInventoryApi()) return salesOverviewMock.transactions.find((item) => item.id === id);
    const { transaction } = await inventoryRequest(`/transactions/${encodeURIComponent(id)}`, transactionResponseSchema);
    return salesTransactionSchema.parse({ id: transaction.id, occurredAt: transaction.createdAt, cupCount: transaction.totalItems, total: transaction.totalAmount, items: transaction.items.map((item) => ({ name: item.productName, quantity: item.quantity, unitPrice: item.unitPrice })), inventoryDeductions: transaction.ingredientConsumption.map((item) => ({ materialName: item.ingredientName, quantity: item.quantity, unit: item.unit })) });
  },
};
