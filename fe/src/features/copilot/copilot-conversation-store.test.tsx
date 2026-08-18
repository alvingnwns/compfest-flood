import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import type { CopilotDisplayMessage } from "./copilot-session";
import {
  CopilotConversationProvider,
  useCopilotConversation,
} from "./copilot-conversation-store";
import {
  copilotStorageKey,
  MAX_COPILOT_MESSAGES,
  MAX_RECENT_API_MESSAGES,
  toRecentCopilotMessages,
  writeCopilotThread,
} from "./copilot-session";

function ThreadHarness({ simulationId }: { simulationId: string }) {
  const conversation = useCopilotConversation(simulationId);
  if (!conversation.hydrated) return <div>Hydrating {simulationId}</div>;
  return (
    <div>
      <div>Thread {simulationId}</div>
      {conversation.thread.messages.map((message) => (
        <div key={message.id}>
          {message.content}
          {message.provider ? ` · ${message.provider} · ${message.grounded ? "grounded" : "ungrounded"}` : ""}
        </div>
      ))}
      <button type="button" onClick={() => conversation.append([{ role: "user", content: `Question ${simulationId}` }])}>
        Add user {simulationId}
      </button>
      <button type="button" onClick={() => conversation.append([{ role: "assistant", content: `Answer ${simulationId}`, provider: "gemini", grounded: true }])}>
        Add assistant {simulationId}
      </button>
      <button type="button" onClick={conversation.clear}>Clear {simulationId}</button>
    </div>
  );
}

describe("Copilot conversation store", () => {
  beforeEach(() => window.sessionStorage.clear());

  it("keeps Simulation A messages when the Copilot route unmounts and returns", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Add user sim-a" }));
    expect(screen.getByText("Question sim-a")).toBeInTheDocument();

    rerender(<CopilotConversationProvider><div>Recovery page</div></CopilotConversationProvider>);
    rerender(<CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>);

    expect(await screen.findByText("Question sim-a")).toBeInTheDocument();
  });

  it("restores messages after the application provider is reinitialized", async () => {
    const user = userEvent.setup();
    const first = render(
      <CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Add assistant sim-a" }));
    expect(screen.getByText(/Answer sim-a/)).toBeInTheDocument();
    first.unmount();

    render(<CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>);

    expect(await screen.findByText(/Answer sim-a · gemini · grounded/)).toBeInTheDocument();
  });

  it("isolates Simulation A and B and restores each thread independently", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Add user sim-a" }));

    rerender(<CopilotConversationProvider><ThreadHarness simulationId="sim-b" /></CopilotConversationProvider>);
    expect(await screen.findByText("Thread sim-b")).toBeInTheDocument();
    expect(screen.queryByText("Question sim-a")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add user sim-b" }));

    rerender(<CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>);
    expect(await screen.findByText("Question sim-a")).toBeInTheDocument();
    expect(screen.queryByText("Question sim-b")).not.toBeInTheDocument();
  });

  it("clears only the current simulation thread", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Add user sim-a" }));
    rerender(<CopilotConversationProvider><ThreadHarness simulationId="sim-b" /></CopilotConversationProvider>);
    await user.click(await screen.findByRole("button", { name: "Add user sim-b" }));
    await user.click(screen.getByRole("button", { name: "Clear sim-b" }));

    expect(window.sessionStorage.getItem(copilotStorageKey("sim-b"))).toBeNull();
    expect(window.sessionStorage.getItem(copilotStorageKey("sim-a"))).not.toBeNull();
    rerender(<CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>);
    expect(await screen.findByText("Question sim-a")).toBeInTheDocument();
  });

  it("persists only whitelisted display fields and bounds stored history", () => {
    const polluted = Array.from({ length: MAX_COPILOT_MESSAGES + 5 }, (_, index) => ({
      id: index,
      role: index % 2 ? "assistant" : "user",
      content: `Visible message ${index}`,
      provider: index % 2 ? "qwen" : undefined,
      grounded: index % 2 ? true : undefined,
      apiKey: "must-not-be-stored",
      copilotContext: { raw: true },
      workbookContents: "must-not-be-stored",
      reasoning: "must-not-be-stored",
    })) as unknown as CopilotDisplayMessage[];

    writeCopilotThread("sim-private", { messages: polluted, suggestedQuestions: ["Visible suggestion"] });
    const raw = window.sessionStorage.getItem(copilotStorageKey("sim-private")) ?? "";
    const stored = JSON.parse(raw) as { messages: unknown[] };

    expect(stored.messages).toHaveLength(MAX_COPILOT_MESSAGES);
    for (const forbidden of ["apiKey", "copilotContext", "workbookContents", "reasoning", "must-not-be-stored"]) {
      expect(raw).not.toContain(forbidden);
    }
    expect(raw).toContain("Visible suggestion");
  });

  it("keeps the backend recent-message payload at six role/content-only entries", () => {
    const messages = Array.from({ length: 10 }, (_, index): CopilotDisplayMessage => ({
      id: index,
      role: index % 2 ? "assistant" : "user",
      content: `Message ${index}`,
      provider: index % 2 ? "deterministic" : undefined,
      grounded: index % 2 ? true : undefined,
    }));

    const recent = toRecentCopilotMessages(messages);

    expect(recent).toHaveLength(MAX_RECENT_API_MESSAGES);
    expect(recent[0]).toEqual({ role: "user", content: "Message 4" });
    expect(recent.at(-1)).toEqual({ role: "assistant", content: "Message 9" });
    expect(JSON.stringify(recent)).not.toContain("provider");
    expect(JSON.stringify(recent)).not.toContain("grounded");
  });

  it("does not restore a pending state from sessionStorage", async () => {
    writeCopilotThread("sim-a", { messages: [], suggestedQuestions: [] });
    render(<CopilotConversationProvider><ThreadHarness simulationId="sim-a" /></CopilotConversationProvider>);
    await waitFor(() => expect(screen.getByText("Thread sim-a")).toBeInTheDocument());
    expect(window.sessionStorage.getItem(copilotStorageKey("sim-a"))).not.toContain("isSending");
  });
});
