import { vi, describe, it, expect, afterEach } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "api", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PosSimulatorPage } from "./pos-simulator-page";

afterEach(() => vi.unstubAllGlobals());
describe("POS retry safety", () => {
  it("recovers a lost response with the identical payload/key and retains the cart", async () => {
    const posts: RequestInit[] = [];
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method !== "POST") return Response.json({ products: [{ id: "P009", name: "Strawberry Juice", price: 20000, currency: "IDR", isActive: true }] });
      posts.push(init);
      if (posts.length === 1) throw new TypeError("Response lost after commit");
      return Response.json({ transaction: { id: "recovered-sale", createdAt: "2026-09-26T09:00:00Z", totalItems: 1, totalAmount: 20000, currency: "IDR", items: [], ingredientConsumption: [] } });
    }));
    const user = userEvent.setup();
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><PosSimulatorPage /></QueryClientProvider>);
    await user.click(await screen.findByRole("button", { name: "Add +" }));
    await user.click(screen.getByRole("button", { name: "Complete Transaction" }));
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("heading", { name: "Transaction status unknown" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New Order" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Clear Order" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Retry same order" }));
    expect(await screen.findByRole("heading", { name: "Transaction Completed" })).toBeInTheDocument();
    expect(screen.getByText("Transaction ID: recovered-sale")).toBeInTheDocument();
    expect(posts).toHaveLength(2);
    expect(posts[1].body).toBe(posts[0].body);
    expect(posts[1].headers).toEqual(posts[0].headers);
  });
  it("shows a definitive BOM failure without offering uncertain recovery", async () => {
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => init?.method === "POST"
      ? Response.json({ error: { code: "INVALID_BOM", message: "Invalid recipe" } }, { status: 409 })
      : Response.json({ products: [{ id: "P009", name: "Strawberry Juice", price: 20000, currency: "IDR", isActive: true }] })));
    const user = userEvent.setup();
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><PosSimulatorPage /></QueryClientProvider>);
    await user.click(await screen.findByRole("button", { name: "Add +" }));
    await user.click(screen.getByRole("button", { name: "Complete Transaction" }));
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(await screen.findByText("INVALID_BOM: Invalid recipe")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry same order" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back to Order" }));
    expect(screen.getByRole("button", { name: "Clear Order" })).toBeEnabled();
  });
});
