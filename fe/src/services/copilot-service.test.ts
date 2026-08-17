import { afterEach, describe, expect, it, vi } from "vitest";
import { publicEnv } from "@/config/public-env";
import { copilotService } from "./copilot-service";

describe("copilot service", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts bounded conversation context and validates a grounded response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      answer: "Grounded answer.", provider: "gemini", grounded: true, suggestedQuestions: [],
    }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await copilotService.ask("sim-001", {
      message: "Why this route?",
      recentMessages: [{ role: "user", content: "Explain the plan." }],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      `${publicEnv.NEXT_PUBLIC_API_BASE_URL}/api/simulations/sim-001/copilot`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(response.grounded).toBe(true);
    expect(response.provider).toBe("gemini");
  });

  it("rejects an ungrounded backend response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      answer: "Unsupported", provider: "gemini", grounded: false, suggestedQuestions: [],
    }), { status: 200 })));
    await expect(copilotService.ask("sim-001", { message: "Explain", recentMessages: [] })).rejects.toThrow();
  });

  it("accepts a grounded Qwen fallback response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      answer: "Grounded Qwen answer.", provider: "qwen", grounded: true, suggestedQuestions: [],
      fallbackReason: "gemini_provider_error",
    }), { status: 200, headers: { "Content-Type": "application/json" } })));

    const response = await copilotService.ask("sim-001", { message: "Explain", recentMessages: [] });

    expect(response.provider).toBe("qwen");
    expect(response.grounded).toBe(true);
  });
});
