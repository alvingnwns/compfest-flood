import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
vi.mock("@/mocks/inventory-data", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/mocks/inventory-data")>();
  return { inventoryOverviewMock: { ...original.inventoryOverviewMock, materials: original.inventoryOverviewMock.materials.map((material) => material.id === "nasi" ? { ...material, issue: "shortage-risk" } : material) } };
});
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InventoryPage } from "./inventory-page";
import styles from "./inventory.module.css";
import { InventoryLanguageProvider } from "@/components/providers/inventory-language-provider";

describe("InventoryPage", () => {
  it("sorts by displayed material names in both directions and updates when the language changes", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    window.localStorage.clear();
    render(<QueryClientProvider client={client}><InventoryLanguageProvider><InventoryPage /></InventoryLanguageProvider></QueryClientProvider>);
    await screen.findByRole("heading", { name: "Stock Movements" });
    const names = () => within(screen.getByRole("region", { name: /Warehouse stock movements|Pergerakan stok gudang/ })).getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent);

    await user.click(screen.getByRole("button", { name: "Material" }));
    expect(names()).toEqual(["Cheese", "Chicken", "Flour", "Rice", "Salt", "Tomato"]);
    expect(screen.getByRole("columnheader", { name: "Material" })).toHaveAttribute("aria-sort", "ascending");
    await user.click(screen.getByRole("button", { name: "Material" }));
    expect(names()).toEqual(["Tomato", "Salt", "Rice", "Flour", "Chicken", "Cheese"]);
    expect(screen.getByRole("columnheader", { name: "Material" })).toHaveAttribute("aria-sort", "descending");

    await user.click(screen.getByRole("button", { name: "Switch to Bahasa Indonesia" }));
    expect(names()).toEqual(["Tomat", "Terigu", "Nasi", "Keju", "Garam", "Ayam"]);
    await user.click(screen.getByRole("button", { name: "Nama Bahan" }));
    expect(names()).toEqual(["Ayam", "Garam", "Keju", "Nasi", "Terigu", "Tomat"]);
  });

  it("filters movements, selects rows, and switches to stock view", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><InventoryPage /></QueryClientProvider>);

    expect(await screen.findByRole("heading", { name: "Stock Movements" })).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("Enter material name..."), "Tomat");
    expect(screen.getByText("Tomato")).toBeInTheDocument();
    expect(screen.queryByText("Rice")).not.toBeInTheDocument();
    await user.clear(screen.getByPlaceholderText("Enter material name..."));
    await user.click(screen.getByRole("tab", { name: "Material Stock" }));
    expect(screen.getByText("Forecast Demand")).toBeInTheDocument();
    const tomatoRow = screen.getByText("Tomato", { selector: "strong" }).closest("tr")!;
    expect(within(tomatoRow).getByText("Low Stock")).toHaveClass(styles.issueWarning);
    expect(within(tomatoRow).getByLabelText("Low stock")).toHaveClass(styles.warning);
    const riceRow = screen.getByText("Rice", { selector: "strong" }).closest("tr")!;
    expect(within(riceRow).getByText("Shortage Risk")).toHaveClass(styles.issueCritical);
    expect(within(riceRow).getByLabelText("Critical stock")).toHaveClass(styles.critical);
    const chickenRow = screen.getByText("Chicken", { selector: "strong" }).closest("tr")!;
    expect(within(chickenRow).getByText("Out of Stock")).toHaveClass(styles.issueCritical);
    const flourRow = screen.getByText("Flour", { selector: "strong" }).closest("tr")!;
    expect(within(flourRow).getByText("Safe")).not.toHaveClass(styles.issueCritical, styles.issueWarning);
    expect(screen.getByRole("button", { name: "Receive Stock" })).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Chicken" })).toBeInTheDocument();
    await user.click(screen.getByText("Tomato", { selector: "strong" }));
    expect(screen.getByRole("heading", { name: "Tomato" })).toBeInTheDocument();
  });
});
