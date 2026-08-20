import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { recoveryFixture, simulationFixture } from "@/mocks/data";
import { RecoveryPage } from "./recovery-page";

vi.mock("next/navigation", () => ({
  usePathname: () => "/recovery",
  useSearchParams: () => new URLSearchParams(`simulation=${simulationFixture.id}&condition=normal`),
}));

vi.mock("@/hooks/use-resilichain-data", () => ({
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
});
