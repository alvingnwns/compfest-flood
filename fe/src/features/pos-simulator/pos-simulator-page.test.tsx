import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { PosSimulatorPage } from "./pos-simulator-page";

describe("PosSimulatorPage", () => {
  it("manages an order and shows insufficient stock", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><PosSimulatorPage /></QueryClientProvider>);
    expect(await screen.findByRole("heading", { name: "Current Order" })).toBeInTheDocument();
    expect(screen.getAllByText(/70\.000/).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Complete Transaction" }));
    expect(screen.getByRole("heading", { name: "Confirm Order" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("heading", { name: "Insufficient Stock" })).toBeInTheDocument();
    expect(screen.getAllByText("200g (0.2 kg)")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Back to Order" }));
    await user.click(screen.getByRole("button", { name: "Decrease Mango Juice" }));
    await user.click(screen.getByRole("button", { name: "Complete Transaction" }));
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("heading", { name: "Transaction Completed" })).toBeInTheDocument();
  });
});
