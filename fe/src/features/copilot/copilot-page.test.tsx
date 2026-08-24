import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { disruptionFixture, impactFixture, recoveryFixture, scenarioFixture, simulationFixture } from "@/mocks/data";
import { CopilotPage } from "./copilot-page";
import { CopilotConversationProvider } from "./copilot-conversation-store";

const mocks = vi.hoisted(() => ({
  simulationId: "",
  mutateAsync: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/copilot",
  useSearchParams: () => new URLSearchParams(mocks.simulationId ? `simulation=${mocks.simulationId}` : ""),
}));

vi.mock("@/hooks/use-aruna-data", () => ({
  useSimulation: () => ({ data: mocks.simulationId ? simulationFixture : undefined, isLoading: false, isError: false, refetch: vi.fn() }),
  useScenario: () => ({ data: scenarioFixture }),
  useDisruptionAnalysis: () => ({ data: disruptionFixture }),
  useRecoveryPlan: () => ({ data: recoveryFixture }),
  useImpactComparison: () => ({ data: impactFixture }),
  useAskCopilot: () => ({ isPending: false, isError: false, mutateAsync: mocks.mutateAsync }),
}));

describe("Copilot page", () => {
  beforeEach(() => {
    mocks.simulationId = "";
    mocks.mutateAsync.mockReset();
    window.sessionStorage.clear();
  });

  const renderPage = () => render(<CopilotConversationProvider><CopilotPage /></CopilotConversationProvider>);

  it("requires a current simulation instead of hallucinating context", () => {
    renderPage();
    expect(screen.getByText("Jalankan simulasi terlebih dahulu")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Buka Skenario/i })).toHaveAttribute("href", "/scenario");
  });

  it("sends a suggested question and renders a grounded provider answer", async () => {
    mocks.simulationId = simulationFixture.id;
    mocks.mutateAsync.mockResolvedValue({
      answer: "The route follows the recorded optimizer rationale.",
      provider: "gemini",
      grounded: true,
      suggestedQuestions: ["Which orders remain at risk?"],
    });
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Konteks Simulasi Saat Ini")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Kenapa rute ini dipilih?" }));

    const answer = await screen.findByText("The route follows the recorded optimizer rationale.");
    expect(answer).toBeInTheDocument();
    expect(answer).toHaveClass("whitespace-pre-wrap", "break-words");
    expect(screen.getByText(/Gemini AI Aktif \(Grounded\)/i)).toBeInTheDocument();
    expect(mocks.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ id: simulationFixture.id }));
  });

  it("sends the immediately previous user and assistant turns without provider metadata", async () => {
    mocks.simulationId = simulationFixture.id;
    mocks.mutateAsync
      .mockResolvedValueOnce({
        answer: "Rencana pemulihan mencakup tindakan operasional yang telah dihitung.",
        provider: "qwen",
        grounded: true,
        suggestedQuestions: [],
      })
      .mockResolvedValueOnce({
        answer: "Rinciannya tetap membahas rencana pemulihan.",
        provider: "qwen",
        grounded: true,
        suggestedQuestions: [],
      });
    const user = userEvent.setup();
    renderPage();

    const input = await screen.findByRole("textbox", { name: /Tanyakan ARUNA Copilot/i });
    await user.type(input, "jelaskan tentang rencana pemulihannya");
    await user.click(screen.getByRole("button", { name: /Kirim|Send/i }));
    await screen.findByText("Rencana pemulihan mencakup tindakan operasional yang telah dihitung.");

    await user.type(input, "iya jelaskan per detailnya");
    await user.click(screen.getByRole("button", { name: /Kirim|Send/i }));
    await screen.findByText("Rinciannya tetap membahas rencana pemulihan.");

    expect(mocks.mutateAsync).toHaveBeenNthCalledWith(2, {
      id: simulationFixture.id,
      request: {
        message: "iya jelaskan per detailnya",
        recentMessages: [
          { role: "user", content: "jelaskan tentang rencana pemulihannya" },
          { role: "assistant", content: "Rencana pemulihan mencakup tindakan operasional yang telah dihitung." },
        ],
      },
    });
  });
});
