import { act, cleanup, render, screen, within } from "@testing-library/react";
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
  it("shows all five juice-production slides in both languages with white and yellow headings", async () => {
    const user = userEvent.setup();
    renderLanding();
    const headings = {
      en: [["Manage Juice Production", "Smarter"], ["Forecast Juice Demand", "Earlier"], ["Understand Your", "Ingredient Needs More Accurately"], ["Identify Risks", "Of Stock Shortages"], ["Determine When and", "How Much to Restock"]],
      id: [["Kelola Produksi Jus", "Lebih Cerdas"], ["Prediksi Permintaan Jus", "Lebih Awal"], ["Ketahui Kebutuhan", "Bahan Baku Lebih Tepat"], ["Kenali Risiko", "Kekurangan Stok"], ["Tentukan Waktu dan", "Jumlah Restock"]],
    };
    for (const locale of ["en", "id"] as const) {
      if (locale === "id") await user.click(screen.getByRole("button", { name: "Switch to Indonesian" }));
      for (const [index, lines] of headings[locale].entries()) {
        await user.click(screen.getByRole("button", { name: `${locale === "en" ? "Go to slide" : "Buka slide"} ${index + 1}` }));
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toHaveTextContent(lines.join(""));
        expect(heading.querySelectorAll("span.text-white")).toHaveLength(1);
        expect([...heading.querySelectorAll("span")].filter((span) => span.classList.contains("text-[var(--color-caution)]"))).toHaveLength(1);
      }
    }
    expect(screen.getByRole("heading", { name: "Produksi Lebih Terencana, Bahan Lebih Terkendali" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Siapkan Bahan. Lancarkan Produksi." })).toBeInTheDocument();
    expect(screen.getByText("Owner meninjau rekomendasi dan menentukan rencana produksi berikutnya.")).toBeInTheDocument();
    expect(screen.getByText("Ketahui berapa banyak buah dan bahan lain yang diperlukan untuk memenuhi permintaan.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ganti ke bahasa Inggris" }));
    expect(screen.getByRole("heading", { name: "Better-Planned Production, Better-Controlled Ingredients" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Prepare Ingredients. Keep Production Running." })).toBeInTheDocument();
    expect(screen.getByText("The owner reviews recommendations and decides on the next production plan.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go to slide 5" })).toHaveAttribute("aria-current", "true");
  });

  it("renders exactly five dynamic indicators with only the current slide highlighted", async () => {
    const user = userEvent.setup();
    const { container } = renderLanding();
    const indicators = within(screen.getByRole("group", { name: "Choose a slide" })).getAllByRole("button");
    expect(indicators).toHaveLength(5);
    expect(container.querySelector('img[src*="inventory-dots.svg"]')).toBeNull();
    const expectActive = (index: number) => {
      indicators.forEach((indicator, position) => {
        if (position === index) {
          expect(indicator).toHaveAttribute("aria-current", "true");
          expect(indicator.firstElementChild).toHaveClass("bg-accent");
        } else {
          expect(indicator).not.toHaveAttribute("aria-current");
          expect(indicator.firstElementChild).toHaveClass("bg-white/40");
        }
      });
    };
    expectActive(0);
    await user.click(indicators[4]);
    expectActive(4);
    await user.click(screen.getByRole("button", { name: "Next slide" }));
    expectActive(0);
    await user.click(screen.getByRole("button", { name: "Previous slide" }));
    expectActive(4);
  });

  it("defaults to English, links to overview, and switches all content to Indonesian", async () => {
    const user = userEvent.setup();
    renderLanding();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage Juice Production");
    expect(screen.getByRole("heading", { name: "From Sales to Production Plans" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "EXPLORE NOW!" })).toHaveAttribute("href", "/ringkasan");
    expect(screen.getByRole("link", { name: "OPTIMIZE YOUR PRODUCTION" })).toHaveAttribute("href", "/ringkasan");
    expect(screen.queryByText(/banjir|flood|Random Forest/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch to Indonesian" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Kelola Produksi Jus");
    expect(screen.getByRole("heading", { name: "Dari Penjualan Menjadi Rencana Produksi" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "OPTIMALKAN PRODUKSI ANDA" })).toHaveAttribute("href", "/ringkasan");
    await user.click(screen.getByRole("button", { name: "Ganti ke bahasa Inggris" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage Juice Production");
  });
  it("navigates all five slides and uses the corresponding local assets", async () => {
    const user = userEvent.setup();
    renderLanding();
    await user.click(screen.getByRole("button", { name: "Next slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Forecast Juice Demand");
    expect(screen.getByRole("img", { name: "Demand forecast illustration" }).getAttribute("src")).toContain("inventory-forecast.png");
    expect(screen.getByText(/Production no longer has to rely on guesswork alone/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to slide 5" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Determine When and");
    await user.click(screen.getByRole("button", { name: "Next slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage Juice Production");
    await user.click(screen.getByRole("button", { name: "Previous slide" }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Determine When and");
  });
  it("can pause automatic rotation", () => {
    vi.useFakeTimers();
    renderLanding();
    act(() => screen.getByRole("button", { name: "Pause autoplay" }).click());
    act(() => vi.advanceTimersByTime(6000));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage Juice Production");
    act(() => screen.getByRole("button", { name: "Resume autoplay" }).click());
    act(() => vi.advanceTimersByTime(5500));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Forecast Juice Demand");
    expect(screen.getByRole("button", { name: "Go to slide 2" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("button", { name: "Go to slide 1" })).not.toHaveAttribute("aria-current");
  });
  it("does not auto-rotate when reduced motion is requested", () => {
    vi.useFakeTimers();
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
      matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn(),
    }));
    renderLanding();
    act(() => vi.advanceTimersByTime(6000));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Manage Juice Production");
    expect(screen.queryByRole("button", { name: "Pause autoplay" })).not.toBeInTheDocument();
  });
});
