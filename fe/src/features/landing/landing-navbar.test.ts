import { describe, expect, it } from "vitest";
import { LANDING_NAVBAR_SOLID_Y, shouldUseSolidLandingNavbar } from "./landing-page";

describe("landing navbar scroll state", () => {
  it("stays transparent at the top and becomes solid at the threshold", () => {
    expect(shouldUseSolidLandingNavbar(0)).toBe(false);
    expect(shouldUseSolidLandingNavbar(LANDING_NAVBAR_SOLID_Y - 1)).toBe(false);
    expect(shouldUseSolidLandingNavbar(LANDING_NAVBAR_SOLID_Y)).toBe(true);
    expect(shouldUseSolidLandingNavbar(240)).toBe(true);
  });
});
