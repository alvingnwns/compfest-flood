import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SalesPage } from "./sales-page";

describe("SalesPage", () => {
  it("filters transactions and updates the selected detail", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><SalesPage /></QueryClientProvider>);

    expect(await screen.findByText("Today's Total Revenue")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("Search transaction ID..."), "00123");
    expect(screen.getAllByText("TRS-00123").length).toBeGreaterThan(0);
    expect(screen.queryByText("TRS-00122")).not.toBeInTheDocument();
    await user.click(screen.getByText("TRS-00123", { selector: "td" }));
    expect(screen.getAllByText("TRS-00123").length).toBeGreaterThan(1);
    expect(screen.queryByText("Source")).not.toBeInTheDocument();
    expect(screen.queryByText("Cashier POS")).not.toBeInTheDocument();
    // Mock data mode has no backend to import into.
    expect(screen.queryByRole("button", { name: /Import Sales History/ })).not.toBeInTheDocument();
  });
});
