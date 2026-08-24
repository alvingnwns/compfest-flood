import { describe, expect, it } from "vitest";
import type { ImpactComparison } from "@/domain/impact";
import { impactCsv, impactExportPayload, type ImpactExportContext } from "./export-service";

const context: ImpactExportContext = {
  scenario: {
    id: "scenario-jakarta-20250304",
    label: "Pola Hujan Relatif Rendah (Simulasi Kondisi)",
    analysisMode: "scenario-simulation",
    operationalCondition: "Normal",
    rainfallScenario: "Q1",
  },
};

const readyImpact: ImpactComparison = {
  simulationId: "sim-q1-ready",
  recoveryStatus: "ready",
  businessDataSource: "demo",
  metrics: [
    { key: "orders-fulfilled", baseline: 18, recovery: 20, total: 20 },
    { key: "on-time-delivery", baseline: 0.7, recovery: 0.8 },
    { key: "failed-orders", baseline: 1, recovery: 0 },
    {
      key: "average-delay",
      baseline: 0.2,
      recovery: 0.6,
      baselineObservationCount: 19,
      recoveryObservationCount: 20,
    },
    { key: "sales-exposure-risk", baseline: 8_000_000, recovery: 0, currency: "IDR" },
  ],
  actionCounts: { manufacturing: 2, logistics: 16, commerce: 20 },
};

function noFeasibleImpact(): ImpactComparison {
  return {
    ...readyImpact,
    simulationId: "sim-no-feasible",
    recoveryStatus: "no-feasible-plan",
    metrics: [
      { key: "orders-fulfilled", baseline: 0, recovery: 0, total: 20 },
      { key: "on-time-delivery", baseline: 0, recovery: 0 },
      { key: "failed-orders", baseline: 20, recovery: 20 },
      {
        key: "average-delay",
        baseline: 0,
        recovery: 0,
        baselineObservationCount: 0,
        recoveryObservationCount: 0,
      },
      { key: "sales-exposure-risk", baseline: 149_000_000, recovery: 149_000_000, currency: "IDR" },
    ],
    actionCounts: { manufacturing: 0, logistics: 0, commerce: 0 },
  };
}

describe("Impact exports", () => {
  it("exports ready KPI values with scenario, source, status, delta, and trend", () => {
    const csv = impactCsv(readyImpact, context);

    expect(csv).toContain("ID Simulasi,sim-q1-ready");
    expect(csv).toContain("ID Skenario,scenario-jakarta-20250304");
    expect(csv).toContain("Skenario,Pola Hujan Relatif Rendah (Simulasi Kondisi)");
    expect(csv).toContain("Mode Analisis,scenario-simulation");
    expect(csv).toContain("Kondisi Operasional,Normal");
    expect(csv).toContain("Pola Hujan,Q1");
    expect(csv).toContain("Sumber Data Bisnis,demo");
    expect(csv).toContain("Status Pemulihan,ready");
    expect(csv).toContain("orders-fulfilled,Pesanan Terpenuhi,18/20,20/20,Naik 2 pesanan,improved");
    expect(csv).toContain("on-time-delivery,Pengiriman Tepat Waktu,70%,80%,Naik 10 poin persentase,improved");
    expect(csv).toContain("average-delay,Rata-rata Keterlambatan,0.2m,0.6m");
  });

  it("exports N/A rather than a zero-minute claim when no delay observations exist", () => {
    const csv = impactCsv(noFeasibleImpact(), context);
    const delayRow = csv.split("\n").find((row) => row.startsWith("average-delay,"));

    expect(delayRow).toContain("N/A,N/A,Tidak tersedia,unavailable");
    expect(delayRow).toContain(",0,0,,0,0,menit");
    expect(delayRow).not.toContain("Rata-rata Keterlambatan,0m");
    expect(csv).toContain("Status Pemulihan,no-feasible-plan");
  });

  it("exports a worsening lower-is-better metric with the verified trend", () => {
    const impact: ImpactComparison = {
      ...readyImpact,
      metrics: readyImpact.metrics.map((metric) =>
        metric.key === "sales-exposure-risk"
          ? { ...metric, baseline: 2_100_000, recovery: 8_200_000 }
          : metric,
      ),
    };
    const csv = impactCsv(impact, context);

    expect(csv).toContain(
      'sales-exposure-risk,Risiko Paparan Penjualan,"Rp 2,1 jt","Rp 8,2 jt","Naik Rp 6,1 jt",worsened',
    );
  });

  it("exports a partial plan without labeling it ready", () => {
    const partialImpact: ImpactComparison = {
      ...readyImpact,
      simulationId: "sim-partial",
      recoveryStatus: "partial",
      metrics: [
        { key: "orders-fulfilled", baseline: 4, recovery: 5, total: 20 },
        { key: "on-time-delivery", baseline: 0.4, recovery: 0.6 },
        { key: "failed-orders", baseline: 15, recovery: 14 },
        {
          key: "average-delay",
          baseline: 1.5,
          recovery: 1,
          baselineObservationCount: 5,
          recoveryObservationCount: 6,
        },
        { key: "sales-exposure-risk", baseline: 12_000_000, recovery: 9_000_000, currency: "IDR" },
      ],
    };
    const csv = impactCsv(partialImpact, context);

    expect(csv).toContain("Status Pemulihan,partial");
    expect(csv).toContain("orders-fulfilled,Pesanan Terpenuhi,4/20,5/20");
    expect(csv).toContain("failed-orders,Pesanan Gagal,15,14");
    expect(csv).toContain("on-time-delivery,Pengiriman Tepat Waktu,40%,60%");
    expect(csv).toContain("average-delay,Rata-rata Keterlambatan,1.5m,1m");
    expect(csv).toContain("sales-exposure-risk,Risiko Paparan Penjualan,Rp 12 jt,Rp 9 jt");
    expect(csv).not.toContain("Status Pemulihan,ready");
  });

  it("exports a custom business source without business workbook or Copilot data", () => {
    const customImpact: ImpactComparison = {
      ...readyImpact,
      simulationId: "sim-custom-ready",
      businessDataSource: "custom",
      metrics: [
        { key: "orders-fulfilled", baseline: 2, recovery: 2, total: 2 },
        { key: "on-time-delivery", baseline: 1, recovery: 0.5 },
        { key: "failed-orders", baseline: 0, recovery: 0 },
        {
          key: "average-delay",
          baseline: 0,
          recovery: 1,
          baselineObservationCount: 2,
          recoveryObservationCount: 2,
        },
        { key: "sales-exposure-risk", baseline: 0, recovery: 0, currency: "IDR" },
      ],
      actionCounts: { manufacturing: 1, logistics: 2, commerce: 2 },
    };
    const payload = impactExportPayload(customImpact, context);
    const serialized = JSON.stringify(payload);
    const fulfilled = payload.metrics.find((metric) => metric.id === "orders-fulfilled");

    expect(payload.businessDataSource).toBe("custom");
    expect(fulfilled?.recovery.display).toBe("2/2");
    expect(serialized).not.toContain("20/20");
    expect(serialized).not.toMatch(/workbook|copilot|recentMessages|apiKey|secret/i);
  });

  it("builds contextual JSON metrics with deltas and observation availability", () => {
    const payload = impactExportPayload(noFeasibleImpact(), context);
    const delay = payload.metrics.find((metric) => metric.id === "average-delay");

    expect(payload.scenario).toEqual(context.scenario);
    expect(payload.businessDataSource).toBe("demo");
    expect(payload.recoveryStatus).toBe("no-feasible-plan");
    expect(delay).toMatchObject({
      baseline: { raw: 0, display: "N/A", available: false, observationCount: 0 },
      recovery: { raw: 0, display: "N/A", available: false, observationCount: 0 },
      delta: { raw: null, display: "Tidak tersedia", trend: "unavailable" },
    });
  });
});
