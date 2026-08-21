import {
  persistedCopilotThreadSchema,
  type CopilotConversationMessage,
  type PersistedCopilotMessage,
} from "@/domain/copilot";

export const MAX_COPILOT_MESSAGES = 40;
export const MAX_RECENT_API_MESSAGES = 6;

export type CopilotDisplayMessage = PersistedCopilotMessage & { id: number };
export type CopilotThread = {
  messages: CopilotDisplayMessage[];
  suggestedQuestions: string[];
};

export const emptyCopilotThread = (): CopilotThread => ({ messages: [], suggestedQuestions: [] });

export const copilotStorageKey = (simulationId: string) => `ARUNA:copilot:${simulationId}`;

export function readCopilotThread(simulationId: string, nextId: () => number): CopilotThread {
  if (typeof window === "undefined") return emptyCopilotThread();
  try {
    const raw = window.sessionStorage.getItem(copilotStorageKey(simulationId));
    if (!raw) return emptyCopilotThread();
    const stored = persistedCopilotThreadSchema.parse(JSON.parse(raw));
    return {
      messages: stored.messages.map((message) => ({ ...message, id: nextId() })),
      suggestedQuestions: stored.suggestedQuestions,
    };
  } catch {
    return emptyCopilotThread();
  }
}

export function writeCopilotThread(simulationId: string, thread: CopilotThread): void {
  if (typeof window === "undefined") return;
  const persisted = persistedCopilotThreadSchema.parse({
    version: 1,
    messages: thread.messages.slice(-MAX_COPILOT_MESSAGES).map(({ role, content, provider, grounded }) => ({
      role,
      content,
      ...(provider ? { provider } : {}),
      ...(grounded ? { grounded } : {}),
    })),
    suggestedQuestions: thread.suggestedQuestions.slice(0, 6),
  });
  try {
    window.sessionStorage.setItem(copilotStorageKey(simulationId), JSON.stringify(persisted));
  } catch {
    // Conversation remains available in application memory when browser storage is unavailable.
  }
}

export function removeCopilotThread(simulationId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(copilotStorageKey(simulationId));
  } catch {
    // Application-memory clearing still succeeds when browser storage is unavailable.
  }
}

export function toRecentCopilotMessages(messages: CopilotDisplayMessage[]): CopilotConversationMessage[] {
  return messages.slice(-MAX_RECENT_API_MESSAGES).map(({ role, content }) => ({ role, content }));
}
