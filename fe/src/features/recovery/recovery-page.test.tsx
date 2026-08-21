import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { recoveryFixture, simulationFixture } from "@/mocks/data";
import { ProductionView, RecoveryPage } from "./recovery-page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/recovery",
  useSearchParams: () => new URLSearchParams(`simulation=${simulationFixture.id}&condition=normal`),
}));

vi.mock("@/hooks/use-aruna-data", () => ({
  useRecoveryPlan: () => ({
    data: recoveryFixture,
    isLoading: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
  }),
  useSimulation: () => ({
    data: simulationFixture,
    isLoading: false,
    isError: false,
    error: undefined,
    refetch: vi.fn(),
  }),
}));

describe("Recovery page", () => {
  it("switches among the three recovery views", async () => {
    const user = userEvent.setup();
    render(<RecoveryPage />);

    expect(screen.getByRole("heading", { name: "PENYESUAIAN PRODUKSI" })).toBeInTheDocument();
    expect(screen.getByText("Produk A")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Pengalihan Rute" }));
    expect(screen.getByRole("heading", { name: "PENGALIHAN RUTE LOGISTIK" })).toBeInTheDocument();
    expect(screen.getByText("V-02")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Alokasi Perdagangan" }));
    expect(screen.getByRole("heading", { name: "ALOKASI PERDAGANGAN" })).toBeInTheDocument();
    expect(screen.getByText("ORD-014")).toBeInTheDocument();
  });

  it("shows every changed-product suggestion with one grounded plan explanation", () => {
    if (!("manufacturingActions" in recoveryFixture)) throw new Error("Expected a completed recovery fixture");
    render(<RecoveryPage />);

    for (const action of recoveryFixture.manufacturingActions) {
      expect(screen.getByText(action.what)).toBeInTheDocument();
      expect(screen.queryByText(action.why)).not.toBeInTheDocument();
    }
    expect(screen.getByText(recoveryFixture.manufacturingExplanation.reason)).toBeInTheDocument();
    expect(screen.getByText(recoveryFixture.manufacturingExplanation.expectedImpact)).toBeInTheDocument();
    expect(screen.getByText(recoveryFixture.manufacturingExplanation.reason)).toHaveTextContent("Produk A");
    expect(screen.getByText(recoveryFixture.manufacturingExplanation.reason)).toHaveTextContent("Produk B");
  });

  it("does not invent an adjustment when production is unchanged", () => {
    render(
      <ProductionView
        actions={[{
          id: "mfg-steady",
          productId: "prod-a",
          productName: "Produk A",
          baselineQuantity: 20,
          recoveryQuantity: 20,
          changeQuantity: 0,
          what: "Pertahankan produksi Produk A sebesar 20 unit.",
          why: "Hasil optimasi mempertahankan kuantitas produksi Produk A.",
          expectedImpact: "Kuantitas produksi Produk A tetap 20 unit.",
        }]}
        explanation={{
          reason: "Hasil optimasi mempertahankan seluruh kuantitas produksi pada skenario ini.",
          expectedImpact: "Rencana pemulihan memenuhi seluruh pesanan.",
        }}
      />,
    );

    expect(screen.getByText("Pertahankan produksi Produk A sebesar 20 unit.")).toBeInTheDocument();
    expect(screen.queryByText(/Naikkan|Kurangi|Sesuaikan/)).not.toBeInTheDocument();
  });
});
