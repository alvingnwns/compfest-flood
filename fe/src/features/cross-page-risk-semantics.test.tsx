import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ImpactComparison } from "@/domain/impact";
import { disruptionFixture } from "@/mocks/data";
import { ImpactPanel } from "./disruption/disruption-page";
import { MetricCard } from "./impact/impact-page";
import { RecoverySummary } from "./recovery/recovery-page";

describe("Q1 cross-page risk semantics", () => {
  it("keeps exposure, recovery decisions, and business outcomes as distinct units", () => {
    const disruption = {
      ...disruptionFixture,
      impact: {
        ...disruptionFixture.impact,
        impactedOrderIds: ["ORD-003", "ORD-008", "ORD-013", "ORD-018"],
        salesExposure: { amount: 30_400_000, currency: "IDR" as const },
      },
    };
    const fulfilled: ImpactComparison["metrics"][number] = {
      key: "orders-fulfilled",
      baseline: 18,
      recovery: 20,
      total: 20,
    };

    render(
      <>
        <ImpactPanel
          data={disruption}
          pending={false}
          issuesOpen={false}
          onPlan={vi.fn()}
          onToggleIssues={vi.fn()}
        />
        <RecoverySummary
          status="ready"
          logisticsAdjustments={13}
          adjustedProducts={2}
          recoverable={20}
          total={20}
        />
        <MetricCard metric={fulfilled} recoveryStatus="ready" />
      </>,
    );

    const exposedMetric = screen.getByText("PESANAN TERPAPAR RISIKO").closest("article");
    expect(exposedMetric).not.toBeNull();
    expect(within(exposedMetric as HTMLElement).getByText("4")).toBeInTheDocument();
    expect(screen.getByText(/PESANAN\s+PULIH PENUH/)).toBeInTheDocument();
    expect(screen.getAllByText("20/20")).toHaveLength(2);
    expect(screen.getByText("Kondisi Awal").parentElement).toHaveTextContent("18/20");
    expect(screen.getByTitle(/Tidak berarti pesanan pasti gagal/)).toBeInTheDocument();
    expect(screen.queryByText(/RISIKO\s+DITANGANI/)).not.toBeInTheDocument();
  });
});
