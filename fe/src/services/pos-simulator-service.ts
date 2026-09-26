import { checkoutRequestSchema, checkoutResultSchema, posCatalogueSchema } from "@/domain/pos-simulator";
import { inventoryResponseSchema, shortageResponseSchema, transactionResponseSchema } from "@/domain/inventory-api";
import { posCatalogueMock } from "@/mocks/pos-simulator-data";
import { InventoryApiError, inventoryRequest, mutationHeaders, usesInventoryApi } from "@/lib/inventory-api";
import { getProducts } from "./inventory-api-data";

export const posSimulatorService = {
  getCatalogue: async () => {
    if (!usesInventoryApi()) return posCatalogueSchema.parse(posCatalogueMock);
    const products = await getProducts();
    return posCatalogueSchema.parse({ source: "api", products: products.filter((product) => product.isActive).map((product) => ({ id: product.id, name: product.name, price: product.price, color: "#d5e6ee" })), initialOrder: [] });
  },
  checkout: async (request: unknown, key = crypto.randomUUID()) => {
    const order = checkoutRequestSchema.parse(request);
    if (usesInventoryApi()) {
      try {
        const { transaction } = await inventoryRequest("/transactions", transactionResponseSchema, { method: "POST", headers: mutationHeaders(key), body: JSON.stringify({ ...order, source: "POS_SIMULATOR" }) });
        return checkoutResultSchema.parse({ status: "success", transactionId: transaction.id });
      } catch (error) {
        if (!(error instanceof InventoryApiError) || error.code !== "INSUFFICIENT_INVENTORY") throw error;
        const { shortages } = shortageResponseSchema.parse(error.details);
        const inventory = await inventoryRequest("/inventory", inventoryResponseSchema);
        return checkoutResultSchema.parse({ status: "insufficient-stock", shortages: shortages.map((item) => {
          const ingredient = inventory.items.find((candidate) => candidate.ingredientId === item.ingredientId);
          if (!ingredient) throw new Error("Ingredient details are unavailable.");
          const scale = ingredient.unit === "kg" || ingredient.unit === "l" ? 1_000_000 : ingredient.unit === "g" || ingredient.unit === "ml" ? 1_000 : 1;
          return { materialName: ingredient.ingredientName, required: item.requiredBase / scale, available: item.availableBase / scale, shortage: item.shortfallBase / scale, unit: ingredient.unit };
        }) });
      }
    }
    const products = posCatalogueSchema.parse(posCatalogueMock).products;
    const shortages = order.items.flatMap((item) => {
      const product = products.find((candidate) => candidate.id === item.productId);
      if (!product || product.materialUsageGrams === undefined || product.availableMaterialGrams === undefined) throw new Error("Product recipe is unavailable.");
      const requiredGrams = product.materialUsageGrams * item.quantity;
      return requiredGrams <= product.availableMaterialGrams ? [] : [{ materialName: product.materialName, requiredGrams, availableGrams: product.availableMaterialGrams, shortageGrams: requiredGrams - product.availableMaterialGrams }];
    });
    return checkoutResultSchema.parse(shortages.length ? { status: "insufficient-stock", shortages } : { status: "success", transactionId: "TRS-00125" });
  },
};
