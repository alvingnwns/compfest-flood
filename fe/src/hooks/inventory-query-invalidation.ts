import type { QueryClient } from "@tanstack/react-query";
const prefixes = ["inventory", "inventory-dashboard", "inventory-sales", "inventory-demand", "inventory-risk", "inventory-stock-risk", "inventory-optimization", "inventory-forecast", "stock-risk"];
export const invalidateInventoryQueries = (client: QueryClient) => client.invalidateQueries({ predicate: (query) => typeof query.queryKey[0] === "string" && prefixes.includes(query.queryKey[0]) });
