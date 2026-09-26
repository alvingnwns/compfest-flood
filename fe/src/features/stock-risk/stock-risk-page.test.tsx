import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StockRiskPage } from "./stock-risk-page";

describe("StockRiskPage", () => {
  it("renders risk analysis and updates selected material detail", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><StockRiskPage /></QueryClientProvider>);

    expect(await screen.findByRole("heading", { name: "Raw Material Risk Analysis" })).toBeInTheDocument();
    expect(screen.getByText("-4.0 kg")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Lime" }));
    expect(screen.getByRole("heading", { name: "Lime" })).toBeInTheDocument();
    expect(screen.getByText("1.5 kg")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Current stock and forecast demand comparison by material" })).toBeInTheDocument();
  });
});
