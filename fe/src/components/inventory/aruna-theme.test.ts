import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = (path: string) => readFileSync(resolve(process.cwd(), path), "utf8");

describe("ARUNA juice theme", () => {
  it("defines the juice palette within a scoped theme class", () => {
    const css = source("src/components/inventory/aruna-theme.module.css");
    const palette = {
      background: "#fffaf3", surface: "#ffffff", "surface-low": "#fcfaf5",
      "surface-high": "#f2f6ee", "surface-highest": "#e5eddf", ink: "#24362b",
      muted: "#626f63", outline: "#dce4d8", primary: "#327052",
      "primary-dark": "#214b38", "primary-soft": "#e8f2e7", "secondary-soft": "#e1edd6",
      accent: "#ffb84d", success: "#2f7a4e", danger: "#ba1a1a",
      "danger-soft": "#ffdad6", warning: "#9a6000", caution: "#f2c744",
    };
    for (const [name, color] of Object.entries(palette)) {
      expect(css).toContain(`--color-${name}: ${color};`);
    }
    expect(css).toMatch(/^\.theme\s*\{/);
    expect(css).not.toMatch(/:root|\bbody\s*\{/);
  });

  it("applies the shared scope only to the inventory shell and landing", () => {
    expect(source("src/components/layout/inventory-shell.tsx")).toContain("${theme.theme} ${styles.shell}");
    expect(source("src/features/landing/landing-page.tsx")).toContain("${theme.theme} overflow-x-hidden");
  });

  it("keeps the requested section headings bold", () => {
    const risk = source("src/features/stock-risk/stock-risk.module.css");
    expect(risk).toMatch(/\.projectionCard h2\s*\{[^}]*font-weight: 700/);
    const optimization = source("src/features/optimization-plan/optimization-plan.module.css");
    expect(optimization).toMatch(/\.tableCard > h2\s*\{[^}]*font-weight: 700/);
    expect(optimization).toMatch(/\.detailHeading h2\s*\{[^}]*font-weight: 700/);
    expect(source("src/features/inventory/inventory.module.css")).toMatch(/\.page > h2\s*\{[^}]*font-weight: 700/);
    expect(source("src/features/demand-forecast/demand-forecast.module.css")).toMatch(/\.detailCard h2\s*\{[^}]*font-weight: 700/);
  });

  it("keeps text contrast readable on primary, accent, and surface colors", () => {
    const luminance = (hex: string) => {
      const channels = [1, 3, 5].map((offset) => {
        const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    };
    for (const [foreground, background] of [["#ffffff", "#327052"], ["#24362b", "#ffb84d"], ["#626f63", "#ffffff"], ["#24362b", "#f2c744"]]) {
      const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
      expect((values[0] + 0.05) / (values[1] + 0.05)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("uses dark text on mango actions and soft safe badges", () => {
    const pos = source("src/features/pos-simulator/pos-simulator.module.css");
    expect(pos).toMatch(/\.checkoutButton[^}]*background: var\(--color-accent\); color: var\(--color-ink\)/);
    const risk = source("src/features/stock-risk/stock-risk.module.css");
    expect(risk).toMatch(/\.statusBadge\.normal[^}]*background: var\(--color-primary-soft\); color: var\(--color-ink\)/);
  });
});
