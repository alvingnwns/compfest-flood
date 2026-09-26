import { describe, expect, it } from "vitest";
import { matchesMaterialName, matchesMovementDate, movementBusinessDate } from "./inventory-filters";

describe("inventory name search", () => {
  it("matches only the displayed material name, not its hidden translation", () => {
    expect(matchesMaterialName("Mangga", " mang ", "en")).toBe(true);
    expect(matchesMaterialName("Semangka", "mang", "en")).toBe(false);
    expect(matchesMaterialName("Semangka", "water", "en")).toBe(true);
    expect(matchesMaterialName("Semangka", "mang", "id")).toBe(true);
    expect(matchesMaterialName("Mangga", "stock in", "en")).toBe(false);
    expect(matchesMaterialName("Mangga", "TRS-001", "en")).toBe(false);
  });
});

describe("movement date filtering", () => {
  it("uses WIB rather than the UTC day", () => {
    expect(movementBusinessDate("2026-09-26T18:00:00Z")).toBe("2026-09-27");
    expect(matchesMovementDate("2026-09-26T18:00:00Z", "2026-09-27", "2026-09-27")).toBe(true);
    expect(matchesMovementDate("2026-09-26T18:00:00Z", "2026-09-26", "2026-09-26")).toBe(false);
  });
  it("supports inclusive, one-sided and cleared date ranges", () => {
    const timestamp = "2026-09-27T20:30:00+07:00";
    expect(matchesMovementDate(timestamp, "2026-09-27", "2026-09-27")).toBe(true);
    expect(matchesMovementDate(timestamp, "2026-09-28", "")).toBe(false);
    expect(matchesMovementDate(timestamp, "", "2026-09-26")).toBe(false);
    expect(matchesMovementDate(timestamp, "", "")).toBe(true);
  });
});
