"use client";

import { ArrowRight, Bot, Send, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState, LoadingState } from "@/components/ui/states";
import type { CopilotConversationMessage } from "@/domain/copilot";
import { useAskCopilot, useDisruptionAnalysis, useImpactComparison, useRecoveryPlan, useScenario, useSimulation } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatRisk } from "@/lib/format";

type DisplayMessage = CopilotConversationMessage & {
  id: number;
  provider?: "gemini" | "qwen" | "deterministic";
};

const initialQuestions = [
  "Which supplier is most affected?",
  "What is the biggest bottleneck?",
  "Why was this route chosen?",
  "Which orders remain at risk?",
];

export function CopilotPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("simulation") ?? "";
  const simulation = useSimulation(simulationId);
  const scenario = useScenario();
  const disruption = useDisruptionAnalysis(simulationId);
  const recovery = useRecoveryPlan(simulationId);
  const impact = useImpactComparison(simulationId);
  const ask = useAskCopilot();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState(initialQuestions);
  const nextMessageId = useRef(0);

  const recoveryData = recovery.data && "summary" in recovery.data ? recovery.data : undefined;
  const logisticsAction = recoveryData?.logisticsActions[0];
  const fulfilledMetric = impact.data?.metrics.find((metric) => metric.key === "orders-fulfilled");
  const failedMetric = impact.data?.metrics.find((metric) => metric.key === "failed-orders");
  const salesMetric = impact.data?.metrics.find((metric) => metric.key === "sales-exposure-risk");
  const overallRisk = useMemo(() => {
    const ranking = { low: 0, medium: 1, high: 2, critical: 3 } as const;
    return disruption.data?.roads.reduce<"low" | "medium" | "high" | "critical">(
      (highest, road) => ranking[road.riskLevel] > ranking[highest] ? road.riskLevel : highest,
      "low",
    );
  }, [disruption.data]);

  const submit = async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed || !simulationId || ask.isPending) return;
    const recentMessages = messages.slice(-6).map(({ role, content }) => ({ role, content }));
    const userMessage: DisplayMessage = { id: ++nextMessageId.current, role: "user", content: trimmed };
    setMessages((current) => [...current, userMessage]);
    setInput("");
    try {
      const response = await ask.mutateAsync({ id: simulationId, request: { message: trimmed, recentMessages } });
      setMessages((current) => [
        ...current,
        { id: ++nextMessageId.current, role: "assistant", content: response.answer, provider: response.provider },
      ]);
      setSuggestedQuestions(response.suggestedQuestions);
    } catch {
      // The mutation error is rendered below without replacing conversation history.
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submit(input);
  };

  if (!simulationId) {
    return (
      <AppShell title="ResiliChain Copilot">
        <div className="grid min-h-[calc(100vh-4rem)] place-items-center p-6">
          <section className="card max-w-xl p-8 text-center">
            <ShieldCheck className="mx-auto mb-4 text-primary" size={36} />
            <h1 className="section-title mb-2">Run a simulation first</h1>
            <p className="mb-6 text-sm leading-relaxed text-muted">
              Run a simulation first to give Copilot operational context. Copilot will not answer without computed evidence.
            </p>
            <Link href="/scenario" className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-dark">
              Open Scenario <ArrowRight size={17} />
            </Link>
          </section>
        </div>
      </AppShell>
    );
  }

  if (simulation.isLoading) return <AppShell title="ResiliChain Copilot"><LoadingState label="Loading simulation context…" /></AppShell>;
  if (simulation.isError) return <AppShell title="ResiliChain Copilot"><ErrorState message={simulation.error.message} onRetry={() => void simulation.refetch()} /></AppShell>;

  return (
    <AppShell title="ResiliChain Copilot">
      <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="flex min-h-[calc(100vh-4rem)] flex-col border-r border-outline">
          <header className="border-b border-outline bg-surface px-5 py-4 md:px-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="eyebrow mb-1">Grounded decision explanation</div>
                <h1 className="text-xl font-semibold text-ink">ResiliChain Copilot</h1>
              </div>
              <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary">
                <ShieldCheck size={14} /> Computed context only
              </span>
            </div>
          </header>

          <div className="flex-1 space-y-5 overflow-y-auto p-5 md:p-8">
            {messages.length === 0 && (
              <div className="card border-primary/20 p-6">
                <div className="mb-3 flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary text-white"><Bot size={20} /></span>
                  <div><h2 className="font-semibold text-ink">Interrogate the current plan</h2><p className="text-xs text-muted">Explanations only · no route or optimizer changes</p></div>
                </div>
                <p className="text-sm leading-relaxed text-muted">
                  Ask why a computed route, supplier impact, order allocation, recovery action, or KPI changed. Answers are limited to the current simulation evidence.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <article key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                {message.role === "assistant" && <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary text-white"><Bot size={16} /></span>}
                <div className={`max-w-[82%] rounded-xl px-4 py-3 text-sm leading-relaxed ${message.role === "user" ? "bg-primary text-white" : "border border-outline bg-surface text-ink"}`}>
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                  {message.provider && <div className={`mono mt-2 text-[10px] uppercase ${message.role === "user" ? "text-white/70" : "text-muted"}`}>{message.provider === "gemini" ? "Gemini · grounded" : message.provider === "qwen" ? "Qwen · grounded" : "Deterministic fallback · grounded"}</div>}
                </div>
                {message.role === "user" && <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-surface-high text-muted"><UserRound size={16} /></span>}
              </article>
            ))}
            {ask.isPending && <div className="flex items-center gap-3 text-sm text-muted"><span className="h-2 w-2 animate-pulse rounded-full bg-primary" /> Reviewing computed evidence…</div>}
            {ask.isError && <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft/30 p-3 text-sm text-danger">{ask.error.message}</div>}
          </div>

          <footer className="border-t border-outline bg-surface p-4 md:px-8">
            <div className="mb-3 flex flex-wrap gap-2">
              {suggestedQuestions.map((question) => (
                <button key={question} type="button" onClick={() => void submit(question)} disabled={ask.isPending} className="rounded-full border border-outline bg-surface-low px-3 py-1.5 text-xs font-medium text-muted hover:border-primary/40 hover:text-primary disabled:opacity-50">
                  {question}
                </button>
              ))}
            </div>
            <form onSubmit={onSubmit} className="flex gap-2">
              <label htmlFor="copilot-message" className="sr-only">Ask ResiliChain Copilot</label>
              <input id="copilot-message" value={input} onChange={(event) => setInput(event.target.value)} maxLength={1_000} placeholder="Ask about the current route, recovery plan, or KPI…" className="min-w-0 flex-1 rounded-lg border border-outline bg-background px-4 py-3 text-sm outline-none focus:border-primary" />
              <button type="submit" disabled={!input.trim() || ask.isPending} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50">
                <Send size={16} /> <span className="hidden sm:inline">Send</span>
              </button>
            </form>
          </footer>
        </section>

        <aside className="bg-surface-low p-5 md:p-6">
          <div className="eyebrow mb-4">Current Simulation Context</div>
          <div className="space-y-3">
            <ContextItem label="Scenario" value={scenario.data?.name ?? simulation.data?.scenarioId ?? "Unavailable"} />
            <ContextItem label="Analysis mode" value={simulation.data?.analysisMode === "scenario-simulation" ? `What-if · ${simulation.data.hazard?.rainfallScenario}` : "Historical replay"} />
            <ContextItem label="Business data" value={simulation.data?.businessDataSource === "custom" ? "Custom upload" : "Demo"} />
            <ContextItem label="Overall road risk" value={overallRisk ? formatRisk(overallRisk) : "Loading…"} />
            <ContextItem label="Affected entities" value={disruption.data ? `${disruption.data.impact.impactedSupplierIds.length} suppliers · ${disruption.data.impact.impactedWarehouseIds.length} warehouses` : "Loading…"} />
            <ContextItem label="Selected recovery route" value={logisticsAction ? `${logisticsAction.originalWarehouseName} → ${logisticsAction.recoveryWarehouseName}` : "Not available"} />
            <ContextItem label="Orders fulfilled" value={fulfilledMetric ? `${fulfilledMetric.recovery}/${fulfilledMetric.total}` : recoveryData ? `${recoveryData.summary.recoverableOrders}/${recoveryData.summary.totalOrders}` : "Not available"} />
            <ContextItem label="Failed orders" value={failedMetric ? String(failedMetric.recovery) : "Not available"} />
            <ContextItem label="Sales exposure" value={salesMetric ? formatCompactIdr(salesMetric.recovery) : disruption.data ? formatCompactIdr(disruption.data.impact.salesExposure.amount) : "Loading…"} />
          </div>
          <div className="mt-5 rounded-lg border border-outline bg-surface p-4 text-xs leading-relaxed text-muted">
            Copilot explains already-computed ML, NetworkX, and OR-Tools results. It cannot change routes, allocations, priorities, or KPIs.
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

function ContextItem({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-outline bg-surface p-3"><div className="mono mb-1 text-[10px] uppercase text-muted">{label}</div><div className="text-sm font-semibold text-ink">{value}</div></div>;
}
