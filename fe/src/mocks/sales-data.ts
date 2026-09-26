import type { SalesOverview } from "@/domain/sales";

export const salesOverviewMock = {
  source: "mock",
  businessDate: "2026-09-27",
  summary: { revenue: 3_420_000, transactionCount: 148, cupsSold: 171 },
  transactions: [
    {
      id: "TRS-00124", occurredAt: "2026-09-27T14:23:10+07:00", cupCount: 2, total: 40_000,
      items: [{ name: "Jus Mangga", quantity: 1, unitPrice: 25_000 }, { name: "Jus Alpukat Sedang", quantity: 1, unitPrice: 15_000 }],
      inventoryDeductions: [{ materialName: "Mangga", quantity: 200, unit: "g" }, { materialName: "Alpukat", quantity: 150, unit: "g" }],
    },
    {
      id: "TRS-00123", occurredAt: "2026-09-27T14:15:45+07:00", cupCount: 1, total: 25_000,
      items: [{ name: "Jus Mangga", quantity: 1, unitPrice: 25_000 }],
      inventoryDeductions: [{ materialName: "Mangga", quantity: 200, unit: "g" }],
    },
    {
      id: "TRS-00122", occurredAt: "2026-09-27T13:58:12+07:00", cupCount: 3, total: 65_000,
      items: [{ name: "Jus Mangga", quantity: 2, unitPrice: 25_000 }, { name: "Es Jeruk", quantity: 1, unitPrice: 15_000 }],
      inventoryDeductions: [{ materialName: "Mangga", quantity: 400, unit: "g" }, { materialName: "Jeruk", quantity: 180, unit: "g" }],
    },
    {
      id: "TRS-00121", occurredAt: "2026-09-27T13:42:00+07:00", cupCount: 2, total: 40_000,
      items: [{ name: "Jus Alpukat Sedang", quantity: 2, unitPrice: 20_000 }],
      inventoryDeductions: [{ materialName: "Alpukat", quantity: 300, unit: "g" }],
    },
    {
      id: "TRS-00120", occurredAt: "2026-09-27T13:10:55+07:00", cupCount: 1, total: 20_000,
      items: [{ name: "Jus Alpukat Sedang", quantity: 1, unitPrice: 20_000 }],
      inventoryDeductions: [{ materialName: "Alpukat", quantity: 150, unit: "g" }],
    },
  ],
} satisfies SalesOverview;
