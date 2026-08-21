import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell, navigationTarget } from "./app-shell";

let pathname = "/impact";
let query = new URLSearchParams("simulation=sim%20one&condition=critical-stock");

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useSearchParams: () => query,
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { children: ReactNode; href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("next/image", () => ({
  default: ({ alt }: { alt: string }) => <span role="img" aria-label={alt} />,
}));

describe("AppShell navigation", () => {
  beforeEach(() => {
    pathname = "/impact";
    query = new URLSearchParams("simulation=sim%20one&condition=critical-stock");
  });

  it("preserves simulation context for workflow pages", () => {
    expect(navigationTarget("/recovery", "sim one", "critical-stock")).toBe(
      "/recovery?simulation=sim%20one&condition=critical-stock",
    );
    expect(navigationTarget("/scenario", "sim one", "critical-stock")).toBe("/scenario");
  });

  it("provides a mobile drawer and omits the misleading overview item", async () => {
    const user = userEvent.setup();
    render(<AppShell title="Analisis Dampak"><div>Isi halaman</div></AppShell>);
    expect(screen.queryByText("Ringkasan")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Buka menu navigasi" }));
    const mobileNav = screen.getByRole("navigation", { name: "Navigasi utama mobile" });
    expect(mobileNav).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Rencana Pemulihan" })[1]).toHaveAttribute(
      "href",
      "/recovery?simulation=sim%20one&condition=critical-stock",
    );
    await user.click(screen.getByRole("button", { name: "Tutup menu" }));
    expect(screen.queryByRole("navigation", { name: "Navigasi utama mobile" })).not.toBeInTheDocument();
  });
});
