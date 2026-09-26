import type { InventoryOverview } from "@/domain/inventory";

export const inventoryOverviewMock = {
  source: "mock",
  businessDate: "2026-09-27",
  materials: [
    { id: "ayam", name: "Ayam", category: "Protein", quantity: 2, unit: "kg", reorderLevel: 6, predictedDemand: 6, issue: "out-of-stock", dueLabel: "Hari Ini", stockId: "AY-004", supplier: "Supplier A" },
    { id: "tomat", name: "Tomat", category: "Sayuran", quantity: 4, unit: "kg", reorderLevel: 6, predictedDemand: 3, issue: "low-stock", dueLabel: "Besok", stockId: "TM-012", supplier: "Supplier B" },
    { id: "nasi", name: "Nasi", category: "Karbohidrat", quantity: 12, unit: "kg", reorderLevel: 6, predictedDemand: 6, issue: "low-stock", dueLabel: "2 hari", stockId: "NS-009", supplier: "Supplier C" },
    { id: "terigu", name: "Terigu", category: "Bahan Kering", quantity: 20, unit: "kg", reorderLevel: 6, predictedDemand: 6, issue: "normal", dueLabel: ">2 hari", stockId: "TR-020", supplier: "Supplier A" },
    { id: "garam", name: "Garam", category: "Bumbu", quantity: 10, unit: "kg", reorderLevel: 1, predictedDemand: 1, issue: "normal", dueLabel: ">7 hari", stockId: "GR-010", supplier: "Supplier B" },
    { id: "keju", name: "Keju", category: "Dairy", quantity: 20, unit: "kg", reorderLevel: 3, predictedDemand: 3, issue: "surplus", dueLabel: ">7 hari", stockId: "KJ-020", supplier: "Supplier A" },
  ],
  movements: [
    { id: "mov-1", materialId: "ayam", materialName: "Ayam", category: "Kebutuhan Penjualan", quantityChange: -6, unit: "kg", referenceId: "SLS-2345", occurredAt: "2026-09-27T20:30:00+07:00", warningLevel: "critical" },
    { id: "mov-2", materialId: "tomat", materialName: "Tomat", category: "Kebutuhan Penjualan", quantityChange: -3, unit: "kg", referenceId: "SLS-0987", occurredAt: "2026-09-27T20:00:00+07:00", warningLevel: "warning" },
    { id: "mov-3", materialId: "nasi", materialName: "Nasi", category: "Kebutuhan Penjualan", quantityChange: -6, unit: "kg", referenceId: "SLS-5677", occurredAt: "2026-09-27T15:00:00+07:00", warningLevel: null },
    { id: "mov-4", materialId: "terigu", materialName: "Terigu", category: "Stok Masuk", quantityChange: 6, unit: "kg", referenceId: "ADD-1234", occurredAt: "2026-09-27T10:00:00+07:00", warningLevel: null },
    { id: "mov-5", materialId: "garam", materialName: "Garam", category: "Stok Masuk", quantityChange: 1, unit: "kg", referenceId: "ADD-0987", occurredAt: "2026-09-27T09:01:00+07:00", warningLevel: null },
    { id: "mov-6", materialId: "keju", materialName: "Keju", category: "Rusak", quantityChange: -3, unit: "kg", referenceId: "ADJ-4568", occurredAt: "2026-09-27T09:00:00+07:00", warningLevel: null },
  ],
} satisfies InventoryOverview;
