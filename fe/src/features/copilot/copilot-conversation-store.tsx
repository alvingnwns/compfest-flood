"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { PersistedCopilotMessage } from "@/domain/copilot";
import {
  emptyCopilotThread,
  MAX_COPILOT_MESSAGES,
  readCopilotThread,
  removeCopilotThread,
  writeCopilotThread,
  type CopilotDisplayMessage,
  type CopilotThread,
} from "./copilot-session";

type ConversationStore = {
  threads: Record<string, CopilotThread>;
  hydrated: ReadonlySet<string>;
  sending: ReadonlySet<string>;
  hydrate: (simulationId: string) => void;
  append: (simulationId: string, messages: PersistedCopilotMessage[]) => void;
  setSuggestions: (simulationId: string, questions: string[]) => void;
  clear: (simulationId: string) => void;
  setSending: (simulationId: string, value: boolean) => void;
};

const CopilotConversationContext = createContext<ConversationStore | null>(null);

export function CopilotConversationProvider({ children }: { children: React.ReactNode }) {
  const [threads, setThreads] = useState<Record<string, CopilotThread>>({});
  const [hydrated, setHydrated] = useState<Set<string>>(() => new Set());
  const [sending, setSendingState] = useState<Set<string>>(() => new Set());
  const nextMessageId = useRef(0);

  const hydrate = useCallback((simulationId: string) => {
    if (!simulationId) return;
    setThreads((current) => current[simulationId]
      ? current
      : { ...current, [simulationId]: readCopilotThread(simulationId, () => ++nextMessageId.current) });
    setHydrated((current) => new Set(current).add(simulationId));
  }, []);

  const updateThread = useCallback((simulationId: string, update: (current: CopilotThread) => CopilotThread) => {
    if (!simulationId) return;
    setThreads((current) => {
      const nextThread = update(current[simulationId] ?? emptyCopilotThread());
      writeCopilotThread(simulationId, nextThread);
      return { ...current, [simulationId]: nextThread };
    });
  }, []);

  const append = useCallback((simulationId: string, messages: PersistedCopilotMessage[]) => {
    updateThread(simulationId, (current) => ({
      ...current,
      messages: [
        ...current.messages,
        ...messages.map((message): CopilotDisplayMessage => ({ ...message, id: ++nextMessageId.current })),
      ].slice(-MAX_COPILOT_MESSAGES),
    }));
  }, [updateThread]);

  const setSuggestions = useCallback((simulationId: string, questions: string[]) => {
    updateThread(simulationId, (current) => ({ ...current, suggestedQuestions: questions.slice(0, 6) }));
  }, [updateThread]);

  const clear = useCallback((simulationId: string) => {
    if (!simulationId) return;
    setThreads((current) => ({ ...current, [simulationId]: emptyCopilotThread() }));
    removeCopilotThread(simulationId);
  }, []);

  const setSending = useCallback((simulationId: string, value: boolean) => {
    setSendingState((current) => {
      const next = new Set(current);
      if (value) next.add(simulationId);
      else next.delete(simulationId);
      return next;
    });
  }, []);

  const value = useMemo<ConversationStore>(() => ({
    threads,
    hydrated,
    sending,
    hydrate,
    append,
    setSuggestions,
    clear,
    setSending,
  }), [append, clear, hydrate, hydrated, sending, setSending, setSuggestions, threads]);

  return <CopilotConversationContext.Provider value={value}>{children}</CopilotConversationContext.Provider>;
}

export function useCopilotConversation(simulationId: string) {
  const store = useContext(CopilotConversationContext);
  if (!store) throw new Error("useCopilotConversation must be used inside CopilotConversationProvider");
  const { hydrate } = store;

  useEffect(() => hydrate(simulationId), [hydrate, simulationId]);

  return {
    hydrated: !simulationId || store.hydrated.has(simulationId),
    thread: store.threads[simulationId] ?? emptyCopilotThread(),
    isSending: store.sending.has(simulationId),
    append: (messages: PersistedCopilotMessage[]) => store.append(simulationId, messages),
    setSuggestions: (questions: string[]) => store.setSuggestions(simulationId, questions),
    clear: () => store.clear(simulationId),
    setSending: (value: boolean) => store.setSending(simulationId, value),
  };
}
