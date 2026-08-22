import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ImpactComparison } from "@/domain/impact";
import { ImpactSummary } from "./impact-page";

function impact(
  recoveryStatus: ImpactComparison["recoveryStatus"],
  full: number,
  failed: number,
  actionCounts = { manufacturing: 2, logistics: 16, commerce: 20 },
): ImpactComparison {
  return {
    simulationId: `sim-${recoveryStatus}`,
    recoveryStatus,
    businessDataSource: "demo",
    metrics: [
      { key: "orders-fulfilled", baseline: 18, recovery: full, total: 20 },
      { key: "on-time-delivery", baseline: 0.7, recovery: 0.8 },
      { key: "failed-orders", baseline: 1, recovery: failed },
      {
        key: "average-delay",
        baseline: 0.2,
        recovery: 0.6,
        baselineObservationCount: 19,
        recoveryObservationCount: recoveryStatus === "no-feasible-plan" ? 0 : 20 - failed,
      },
      { key: "sales-exposure-risk", baseline: 8_000_000, recovery: 0, currency: "IDR" },
    ],
    actionCounts,
  };
}

function expectSummaryRow(label: string, value: string) {
  const row = screen.getByText(label).parentElement;
  expect(row).not.toBeNull();
  expect(within(row as HTMLElement).getByText(value)).toBeInTheDocument();
}

describe("Impact recovery summary semantics", () => {
  it("uses distinct truthful count labels for a ready result", () => {
    render(<ImpactSummary impact={impact("ready", 20, 0)} />);

    expect(screen.getByRole("region", { name: "Ringkasan Pemulihan" })).toBeInTheDocument();
    expectSummaryRow("Produk dalam Rencana", "2");
    expectSummaryRow("Penyesuaian Logistik", "16");
    expectSummaryRow("Pesanan Dianalisis", "20");
    expect(screen.getByText("20/20")).toBeInTheDocument();
    expect(screen.getByText("Pulih Penuh")).toBeInTheDocument();
    expect(screen.queryByText("Perdagangan")).not.toBeInTheDocument();
  });

  it("separates full, partial, and failed orders for a partial result", () => {
    render(<ImpactSummary impact={impact("partial", 5, 14)} />);

    expect(screen.getByRole("region", { name: "Ringkasan Rencana Parsial" })).toBeInTheDocument();
    expect(screen.getByText("5/20")).toBeInTheDocument();
    expectSummaryRow("Parsial", "1");
    expectSummaryRow("Tidak Terpenuhi", "14");
    expect(screen.queryByText("Siap")).not.toBeInTheDocument();
  });

  it("does not use successful recovery wording for a no-feasible result", () => {
    render(
      <ImpactSummary
        impact={impact("no-feasible-plan", 0, 20, { manufacturing: 0, logistics: 0, commerce: 0 })}
      />,
    );

    expect(screen.getByRole("region", { name: "Ringkasan Hasil Optimizer" })).toBeInTheDocument();
    expectSummaryRow("Produk dalam Rencana", "0");
    expectSummaryRow("Penyesuaian Logistik", "0");
    expectSummaryRow("Pesanan Dianalisis", "20");
    expect(screen.getByText("0/20")).toBeInTheDocument();
    expectSummaryRow("Parsial", "0");
    expectSummaryRow("Tidak Terpenuhi", "20");
    expect(screen.queryByText("Ringkasan Pemulihan")).not.toBeInTheDocument();
    expect(screen.queryByText("Siap")).not.toBeInTheDocument();
  });
});
