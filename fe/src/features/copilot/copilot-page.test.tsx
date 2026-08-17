import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { disruptionFixture, impactFixture, recoveryFixture, scenarioFixture, simulationFixture } from "@/mocks/data";
import { CopilotPage } from "./copilot-page";

const mocks = vi.hoisted(() => ({
  simulationId: "",
  mutateAsync: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/copilot",
  useSearchParams: () => new URLSearchParams(mocks.simulationId ? `simulation=${mocks.simulationId}` : ""),
}));

vi.mock("@/hooks/use-resilichain-data", () => ({
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
  });

  it("requires a current simulation instead of hallucinating context", () => {
    render(<CopilotPage />);
    expect(screen.getByText("Run a simulation first")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Scenario/ })).toHaveAttribute("href", "/scenario");
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
    render(<CopilotPage />);

    expect(screen.getByText("Current Simulation Context")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Why was this route chosen?" }));

    const answer = await screen.findByText("The route follows the recorded optimizer rationale.");
    expect(answer).toBeInTheDocument();
    expect(answer).toHaveClass("whitespace-pre-wrap", "break-words");
    expect(screen.getByText("Gemini · grounded")).toBeInTheDocument();
    expect(mocks.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ id: simulationFixture.id }));
  });
});
