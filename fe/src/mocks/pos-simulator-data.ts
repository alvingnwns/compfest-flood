import type { PosCatalogue } from "@/domain/pos-simulator";

export const posCatalogueMock: PosCatalogue = {
  source: "mock",
  products: [
    { id: "mango", name: "Mango Juice", materialName: "Mangga", materialUsageGrams: 200, price: 25_000, availableMaterialGrams: 200, color: "#ffeed3" },
    { id: "orange", name: "Orange Juice", materialName: "Jeruk Peras", materialUsageGrams: 150, price: 20_000, availableMaterialGrams: 500, color: "#ffe5d1" },
    { id: "avocado", name: "Avocado Juice", materialName: "Alpukat", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 1_200, color: "#e2f6d5" },
    { id: "guava", name: "Guava Juice", materialName: "Jambu", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 900, color: "#c4dbb6" },
    { id: "lemonade", name: "Lemonade", materialName: "Lemon", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 800, color: "#f4f6d5" },
    { id: "apple", name: "Apple Juice", materialName: "Apel", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 900, color: "#f6d5d5" },
    { id: "pineapple", name: "Pineapple Juice", materialName: "Nanas", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 900, color: "#e5e8b3" },
    { id: "banana", name: "Banana Juice", materialName: "Pisang", materialUsageGrams: 180, price: 22_000, availableMaterialGrams: 900, color: "#faffb4" },
  ],
  initialOrder: [{ productId: "mango", quantity: 2 }, { productId: "orange", quantity: 1 }],
};
