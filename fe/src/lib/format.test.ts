import { describe, expect, it } from "vitest";
import { formatCompactIdr, formatMinutes, formatPercent, formatRisk } from "./format";

describe("display formatting", () => {
  it("formats Indonesian currency without embedding scenario values in components", () => {
    expect(formatCompactIdr(8_200_000)).toBe("Rp 8,2 jt");
  });

  it("formats percentages, durations, and risk labels", () => {
    expect(formatPercent(0.82)).toBe("82%");
    expect(formatMinutes(128)).toBe("2j 8m");
    expect(formatRisk("critical")).toBe("Kritis");
  });
});
