import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { InventoryLanguageProvider } from "@/components/providers/inventory-language-provider";
import { LandingPage } from "./landing-page";

function renderLanding() {
  return render(<InventoryLanguageProvider><LandingPage /></InventoryLanguageProvider>);
}
beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
    matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  }));
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("inventory landing page", () => {
  it("defaults to English, links to overview, and switches all content to Indonesian", async () => {
    const user = userEvent.setup();
    renderLanding();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage your business");
    expect(screen.getByRole("heading", { name: "From data to decisions" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Explore now" })).toHaveAttribute("href", "/ringkasan");
    expect(screen.getByRole("link", { name: "Optimize your inventory" })).toHaveAttribute("href", "/ringkasan");
    expect(screen.queryByText(/banjir|flood|Random Forest/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch to Indonesian" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Kelola Bisnis Anda");
    expect(screen.getByRole("heading", { name: "Dari Data Menjadi Keputusan" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Optimalkan stok bisnis Anda" })).toHaveAttribute("href", "/ringkasan");
    await user.click(screen.getByRole("button", { name: "Ganti ke bahasa Inggris" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage your business");
  });
  it("navigates all four slides and uses the corresponding local assets", async () => {
    const user = userEvent.setup();
    renderLanding();
    await user.click(screen.getByRole("button", { name: "Next slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Forecast stock needs");
    expect(screen.getByRole("img", { name: "Demand forecast illustration" }).getAttribute("src")).toContain("inventory-forecast.png");
    expect(screen.getByText(/fallback estimates/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to slide 4" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Plan your purchases");
    await user.click(screen.getByRole("button", { name: "Next slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage your business");
    await user.click(screen.getByRole("button", { name: "Previous slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Plan your purchases");
  });
  it("can pause automatic rotation", () => {
    vi.useFakeTimers();
    renderLanding();
    act(() => screen.getByRole("button", { name: "Pause autoplay" }).click());
    act(() => vi.advanceTimersByTime(6000));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage your business");
    act(() => screen.getByRole("button", { name: "Resume autoplay" }).click());
    act(() => vi.advanceTimersByTime(5500));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Forecast stock needs");
  });
  it("does not auto-rotate when reduced motion is requested", () => {
    vi.useFakeTimers();
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
      matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn(),
    }));
    renderLanding();
    act(() => vi.advanceTimersByTime(6000));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage your business");
    expect(screen.queryByRole("button", { name: "Pause autoplay" })).not.toBeInTheDocument();
  });
});
