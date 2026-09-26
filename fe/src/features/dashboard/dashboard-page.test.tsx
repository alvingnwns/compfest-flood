import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DashboardPage } from "./dashboard-page";
import { InventoryLanguageProvider } from "@/components/providers/inventory-language-provider";

describe("DashboardPage", () => {
  it("shows the Ringkasan data and filters pending actions", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    window.localStorage.clear();
    render(<QueryClientProvider client={client}><InventoryLanguageProvider><DashboardPage /></InventoryLanguageProvider></QueryClientProvider>);

    expect(await screen.findByText("Gross Sales")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to landing page" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Sales" })).toHaveAttribute("href", "/penjualan");
    expect(screen.getByRole("link", { name: "Inventory" })).toHaveAttribute("href", "/gudang");
    expect(screen.getByRole("link", { name: "Demand Forecast" })).toHaveAttribute("href", "/prediksi-permintaan");
    expect(screen.getByRole("link", { name: "Stock Risks" })).toHaveAttribute("href", "/stok-berisiko");
    expect(screen.getByRole("link", { name: "Optimization Plan" })).toHaveAttribute("href", "/rencana-optimasi");
    expect(screen.getByRole("link", { name: "POS Simulator" })).toHaveAttribute("href", "/pos-simulator");
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View More/ })).toHaveAttribute("href", "/rencana-optimasi");
    expect(screen.getByText("Chicken")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Pending actions table" })).toHaveAttribute("tabindex", "0");
    await user.click(screen.getByRole("button", { name: "Expiring" }));
    expect(screen.queryByText("Chicken")).not.toBeInTheDocument();
    expect(screen.getByText("No actions in this category.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch to Bahasa Indonesia" }));
    expect(screen.getByRole("heading", { name: "Ringkasan" })).toBeInTheDocument();
  });
});
