import { describe, expect, it } from "vitest";
import type { ImpactMetric } from "@/domain/impact";
import { formatImpactMetricValue, impactMetricDelta, impactStatusPresentation, noDelayObservationMessage } from "./impact-presentation";

describe("impact presentation semantics", () => {
  it("uses normal success semantics only for a feasible recovery", () => {
    const copy = impactStatusPresentation("ready");
    expect(copy.headline).toBe("DAMPAK PEMULIHAN");
    expect(copy.steps).toContain("Siap");
  });

  it("never uses success wording for a no-feasible outcome", () => {
    const copy = impactStatusPresentation("no-feasible-plan");
    expect(copy.noticeTitle).toMatch(/Tidak Ada Rencana/);
    expect(copy.steps).toContain("Tidak Layak");
    expect(copy.steps).not.toContain("Siap");
    expect(copy.noticeBody).toMatch(/bukan keberhasilan/);
  });

  it("labels partial recovery as requiring review", () => {
    const copy = impactStatusPresentation("partial");
    expect(copy.headline).toMatch(/PARSIAL/);
    expect(copy.steps).toContain("Tinjau");
    expect(copy.steps).not.toContain("Siap");
  });

  it("marks worse exposure as an increase, never an improvement", () => {
    const metric: ImpactMetric = {
      key: "sales-exposure-risk",
      baseline: 2_100_000,
      recovery: 8_200_000,
      currency: "IDR",
    };
    expect(impactMetricDelta(metric)).toEqual({ label: "Naik Rp 6,1 jt", trend: "worsened" });
  });

  it("uses neutral language for unchanged values", () => {
    const metric: ImpactMetric = { key: "failed-orders", baseline: 4, recovery: 4 };
    expect(impactMetricDelta(metric)).toEqual({ label: "Tidak berubah", trend: "unchanged" });
  });

  it("shows N/A when no delivered orders exist for delay", () => {
    const metric: ImpactMetric = {
      key: "average-delay",
      baseline: 25,
      recovery: 0,
      baselineObservationCount: 3,
      recoveryObservationCount: 0,
    };
    expect(formatImpactMetricValue(metric, "recovery")).toBe("N/A");
    expect(impactMetricDelta(metric)).toEqual({ label: "Tidak tersedia", trend: "unavailable" });
    expect(noDelayObservationMessage).toMatch(/Tidak ada pesanan terkirim/);
  });
});
