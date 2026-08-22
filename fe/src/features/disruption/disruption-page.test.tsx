import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { disruptionFixture } from "@/mocks/data";
import { MapLegend } from "./disruption-map";
import { ImpactPanel } from "./disruption-page";

describe("Disruption impact metric semantics", () => {
  it("uses threshold-specific and exposed-order-value labels", () => {
    render(
      <ImpactPanel
        data={disruptionFixture}
        pending={false}
        issuesOpen={false}
        onPlan={vi.fn()}
        onToggleIssues={vi.fn()}
      />,
    );

    expect(screen.getByText("SEGMEN RISIKO TINGGI/KRITIS")).toBeInTheDocument();
    expect(screen.getByText("PEMASOK DENGAN RUTE BERISIKO")).toBeInTheDocument();
    expect(screen.getByText("PESANAN TERPAPAR RISIKO")).toBeInTheDocument();
    expect(screen.queryByText("PESANAN BERISIKO")).not.toBeInTheDocument();
    expect(screen.getByText("NILAI PESANAN BERISIKO")).toBeInTheDocument();
    expect(
      screen.getByText("Paparan risiko sebelum pemulihan berdasarkan rute baseline dan nilai pesanan terkait."),
    ).toBeInTheDocument();
    expect(screen.queryByText("PENJUALAN TERDAMPAK")).not.toBeInTheDocument();
    expect(screen.getByTitle(/Bukan nilai kerugian aktual/)).toBeInTheDocument();
    expect(screen.getByTitle(/Tidak berarti pesanan pasti gagal/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rencanakan Pemulihan" })).toBeInTheDocument();
  });

  it("indicates active focused issue in ImpactPanel", () => {
    render(
      <ImpactPanel
        data={disruptionFixture}
        pending={false}
        issuesOpen={false}
        selectedIssueId="issue-1"
        onPlan={vi.fn()}
        onToggleIssues={vi.fn()}
      />,
    );
    expect(screen.getByText("1 Aktif")).toBeInTheDocument();
  });
});

describe("Disruption Map Legend semantics", () => {
  it("renders risk levels, dashed baseline route, and solid candidate route", () => {
    render(
      <MapLegend
        dynamic={false}
        hasBaseline={true}
        hasCandidate={true}
      />
    );

    expect(screen.getByText("Legenda Peta")).toBeInTheDocument();
    expect(screen.getByText("Rute Awal")).toBeInTheDocument();
    expect(screen.getByText("Kandidat Risk-Aware")).toBeInTheDocument();
    expect(screen.getByText("Kritis")).toBeInTheDocument();
    expect(screen.getByText("Tinggi")).toBeInTheDocument();
    expect(screen.getByText("Sedang")).toBeInTheDocument();
    expect(screen.getByText("Rendah")).toBeInTheDocument();
  });
});
