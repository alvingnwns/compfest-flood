import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { OptimizationPlanPage } from "./optimization-plan-page";

describe("OptimizationPlanPage", () => {
  it("selects recommendations and filters by status", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><OptimizationPlanPage /></QueryClientProvider>);

    expect(await screen.findByRole("heading", { name: "System Optimization Recommendations" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Restock Material Mango" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reduce Purchase" }));
    expect(screen.getByRole("heading", { name: "Reduce Purchase Avocado" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve Plan" })).toBeDisabled();
    await user.click(screen.getByRole("tab", { name: "Approved" }));
    expect(screen.getByText("No plans in this status.")).toBeInTheDocument();
  });
});
