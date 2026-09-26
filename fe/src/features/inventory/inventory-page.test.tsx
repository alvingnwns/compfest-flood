import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { InventoryPage } from "./inventory-page";

describe("InventoryPage", () => {
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
    expect(screen.getByRole("button", { name: "Receive Stock" })).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Chicken" })).toBeInTheDocument();
    await user.click(screen.getByText("Tomato", { selector: "strong" }));
    expect(screen.getByRole("heading", { name: "Tomato" })).toBeInTheDocument();
  });
});
