import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CommerceAction } from "@/domain/recovery";
import { CommerceView } from "./recovery-page";

function commerceAction(overrides: Partial<CommerceAction> = {}): CommerceAction {
  return {
    id: "com-test",
    orderId: "ORD-001",
    storeId: "store-a",
    storeName: "Toko A",
    requestedProductId: "prod-b",
    requestedProductName: "Produk B",
    requestedQuantity: 60,
    priority: "high",
    action: "fulfill",
    allocations: [{ productId: "prod-b", productName: "Produk B", quantity: 60 }],
    what: "Penuhi pesanan dari hasil pemulihan.",
    why: "Berdasarkan hasil optimizer.",
    expectedImpact: "Menjaga pemenuhan pesanan.",
    ...overrides,
  };
}

describe("CommerceView order-allocation semantics", () => {
  it("shows full fulfillment as allocated over requested quantity", () => {
    render(<CommerceView actions={[commerceAction()]} />);

    const card = screen.getByRole("article");
    expect(screen.getByRole("heading", { name: "ALOKASI PESANAN" })).toBeInTheDocument();
    expect(within(card).getByText("ORD-001")).toBeInTheDocument();
    expect(within(card).getByText("Toko A")).toBeInTheDocument();
    expect(within(card).getByText("Penuhi penuh")).toBeInTheDocument();
    expect(within(card).getByText("Produk B")).toBeInTheDocument();
    expect(within(card).getByText("60 / 60 unit")).toBeInTheDocument();
    expect(within(card).getByText("Prioritas pesanan: Tinggi")).toBeInTheDocument();
    expect(within(card).queryByText(/Rekomendasi:|fulfill/)).not.toBeInTheDocument();
  });

  it("derives partial fulfillment from allocated quantity", () => {
    render(<CommerceView actions={[commerceAction({
      orderId: "ORD-002",
      requestedQuantity: 70,
      action: "split",
      allocations: [{ productId: "prod-b", productName: "Produk B", quantity: 40 }],
    })]} />);

    const card = screen.getByRole("article");
    expect(within(card).getByText("Penuhi sebagian")).toBeInTheDocument();
    expect(within(card).getByText("40 / 70 unit")).toBeInTheDocument();
  });

  it("shows zero allocation as unfulfilled rather than delayed fulfillment", () => {
    render(<CommerceView actions={[commerceAction({
      orderId: "ORD-003",
      requestedQuantity: 90,
      action: "delay",
      allocations: [],
    })]} />);

    const card = screen.getByRole("article");
    expect(within(card).getByText("Tidak dapat dipenuhi")).toBeInTheDocument();
    expect(within(card).getByText("0 / 90 unit")).toBeInTheDocument();
    expect(within(card).queryByText("Tunda")).not.toBeInTheDocument();
  });

  it("keeps critical input priority secondary when the order is fully fulfilled", () => {
    render(<CommerceView actions={[commerceAction({
      orderId: "ORD-008",
      requestedQuantity: 80,
      priority: "critical",
      action: "prioritize",
      allocations: [{ productId: "prod-b", productName: "Produk B", quantity: 80 }],
    })]} />);

    const card = screen.getByRole("article");
    expect(within(card).getByText("Penuhi penuh")).toBeInTheDocument();
    expect(within(card).getByText("80 / 80 unit")).toBeInTheDocument();
    expect(within(card).getByText("Prioritas pesanan: Kritis")).toBeInTheDocument();
    expect(within(card).queryByText("Prioritaskan")).not.toBeInTheDocument();
  });

  it("renders custom order and product values from the provided API action", () => {
    render(<CommerceView actions={[commerceAction({
      id: "com-custom",
      orderId: "CUSTOM-LONG-ORDER-9001",
      storeName: "Toko Pelanggan Khusus",
      requestedProductId: "custom-product",
      requestedProductName: "Produk Unggahan Pelanggan",
      requestedQuantity: 37,
      priority: "normal",
      allocations: [{ productId: "custom-product", productName: "Produk Unggahan Pelanggan", quantity: 37 }],
    })]} />);

    expect(screen.getByText("CUSTOM-LONG-ORDER-9001")).toBeInTheDocument();
    expect(screen.getByText("Toko Pelanggan Khusus")).toBeInTheDocument();
    expect(screen.getByText("Produk Unggahan Pelanggan")).toBeInTheDocument();
    expect(screen.getByText("37 / 37 unit")).toBeInTheDocument();
    expect(screen.queryByText(/ORD-001|Produk A|Produk B/)).not.toBeInTheDocument();
  });

  it("makes optimizer-produced substitution explicit", () => {
    render(<CommerceView actions={[commerceAction({
      requestedProductId: "prod-a",
      requestedProductName: "Produk A",
      requestedQuantity: 60,
      action: "substitute",
      allocations: [{ productId: "prod-b", productName: "Produk B", quantity: 60 }],
    })]} />);

    const card = screen.getByRole("article");
    expect(within(card).getByText("Substitusi")).toBeInTheDocument();
    expect(within(card).getByText("60 / 60 unit")).toBeInTheDocument();
    expect(within(card).getByText(/Substitusi: Produk A/)).toHaveTextContent("Produk B");
  });
});
