"use client";

import { ArrowRight, Bot, Send, ShieldCheck, Trash2, UserRound } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useCopilotConversation } from "./copilot-conversation-store";
import { toRecentCopilotMessages } from "./copilot-session";
import { useAskCopilot, useDisruptionAnalysis, useImpactComparison, useRecoveryPlan, useScenario, useSimulation } from "@/hooks/use-resilichain-data";
import { formatCompactIdr, formatRisk } from "@/lib/format";

const initialQuestions = [
  "Apa dampaknya kalau kondisi ini memburuk?",
  "Kalau satu kendaraan tidak tersedia, apa yang bisa terjadi?",
  "Supplier mana yang paling terdampak?",
  "Pesanan mana yang masih beresiko?",
  "Kenapa rute ini dipilih?",
];

export function CopilotPage() {
  const params = useSearchParams();
  const simulationId = params.get("simulation") ?? "";
  const simulation = useSimulation(simulationId);
  const scenario = useScenario();
  const disruption = useDisruptionAnalysis(simulationId);
  const recovery = useRecoveryPlan(simulationId);
  const impact = useImpactComparison(simulationId);
  const ask = useAskCopilot();
  const conversation = useCopilotConversation(simulationId);
  const [input, setInput] = useState("");
  const messageViewport = useRef<HTMLDivElement>(null);
  const { messages, suggestedQuestions } = conversation.thread;
  const visibleQuestions = suggestedQuestions.length > 0 ? suggestedQuestions : messages.length === 0 ? initialQuestions : [];

  const recoveryData = recovery.data && "summary" in recovery.data ? recovery.data : undefined;
  const logisticsAction = recoveryData?.logisticsActions[0];
  const fulfilledMetric = impact.data?.metrics.find(metric => metric.key === "orders-fulfilled");
  const failedMetric = impact.data?.metrics.find(metric => metric.key === "failed-orders");
  const salesMetric = impact.data?.metrics.find(metric => metric.key === "sales-exposure-risk");
  const overallRisk = useMemo(() => {
    const ranking = { low: 0, medium: 1, high: 2, critical: 3 } as const;
    return disruption.data?.roads.reduce<"low" | "medium" | "high" | "critical">((highest, road) => ranking[road.riskLevel] > ranking[highest] ? road.riskLevel : highest, "low");
  }, [disruption.data]);

  useEffect(() => {
    if (messageViewport.current) messageViewport.current.scrollTop = messageViewport.current.scrollHeight;
  }, [conversation.isSending, messages]);

  const submit = async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed || !simulationId || !conversation.hydrated || conversation.isSending || simulation.data?.status !== "completed") return;
    const recentMessages = toRecentCopilotMessages(messages);
    conversation.append([{ role: "user", content: trimmed }]);
    conversation.setSending(true);
    setInput("");
    try {
      const response = await ask.mutateAsync({ id: simulationId, request: { message: trimmed, recentMessages } });
      conversation.append([{ role: "assistant", content: response.answer, provider: response.provider, grounded: response.grounded }]);
      conversation.setSuggestions(response.suggestedQuestions);
    } finally {
      conversation.setSending(false);
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submit(input);
  };

  if (!simulationId) return <AppShell title="ResiliChain Copilot"><div className="grid min-h-[calc(100vh-125px)] place-items-center p-6"><section className="rounded-lg border border-outline bg-white p-8 text-center shadow-sm"><ShieldCheck className="mx-auto mb-4 text-primary" size={36} /><h1 className="mb-2 text-xl font-semibold">Run a simulation first</h1><p className="mb-6 max-w-lg text-sm text-muted">Run a simulation first to give Copilot operational context. Copilot will not answer without computed evidence.</p><Link href="/scenario" className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white">Open Scenario <ArrowRight size={17} /></Link></section></div></AppShell>;
  if (simulation.isLoading) return <AppShell title="ResiliChain Copilot"><LoadingState label="Loading simulation context..." /></AppShell>;
  if (simulation.isError) return <AppShell title="ResiliChain Copilot"><ErrorState message={simulation.error.message} onRetry={() => void simulation.refetch()} /></AppShell>;
  if (!conversation.hydrated) return <AppShell title="ResiliChain Copilot"><LoadingState label="Restoring conversation..." /></AppShell>;

  const contextItems = [
    ["Skenario", scenario.data?.name ?? simulation.data?.scenarioId ?? "Tidak tersedia"],
    ["Data Bisnis", simulation.data?.businessDataSource === "custom" ? "Unggahan sendiri" : "Demo"],
    ["Resiko jalan keseluruhan", overallRisk ? formatRisk(overallRisk) : "Memuat..."],
    ["Pihak terdampak", disruption.data ? `${disruption.data.impact.impactedSupplierIds.length} pemasok dan ${disruption.data.impact.impactedWarehouseIds.length} gudang` : "Memuat..."],
    ["Rute pemulihan", logisticsAction ? `${logisticsAction.originalWarehouseName} - ${logisticsAction.recoveryWarehouseName}` : "Tidak tersedia"],
    ["Pesanan terpenuhi", fulfilledMetric ? `${fulfilledMetric.recovery}/${fulfilledMetric.total}` : recoveryData ? `${recoveryData.summary.recoverableOrders}/${recoveryData.summary.totalOrders}` : "Tidak tersedia"],
    ["Pesanan gagal", failedMetric ? String(failedMetric.recovery) : "Tidak tersedia"],
    ["Penjualan terdampak", salesMetric ? formatCompactIdr(salesMetric.recovery) : disruption.data ? formatCompactIdr(disruption.data.impact.salesExposure.amount) : "Memuat..."],
  ];

  return <AppShell title="ResiliChain Copilot">
    <div className="copilot-pattern grid min-h-[calc(100vh-125px)] xl:h-[calc(100vh-125px)] xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_370px] xl:overflow-hidden">
      <section className="relative flex min-h-[720px] flex-col overflow-hidden border-r border-outline xl:min-h-0">
        {messages.length > 0 && <button type="button" onClick={conversation.clear} disabled={conversation.isSending} aria-label="Hapus percakapan" title="Hapus percakapan" className="absolute left-5 top-5 z-20 grid size-10 place-items-center rounded-full border border-outline bg-white/90 text-muted shadow-sm hover:text-danger disabled:opacity-50"><Trash2 className="size-4" /></button>}

        <div ref={messageViewport} className="flex-1 space-y-6 overflow-y-auto px-6 py-8 md:px-12">
          {messages.length === 0 && <article className="mx-auto mt-4 flex max-w-[780px] items-start gap-4">
            <span className="grid size-14 shrink-0 place-items-center rounded-full bg-primary text-white shadow-md"><Bot className="size-7" /></span>
            <div className="rounded-[25px] bg-[#dedede] px-7 py-6 text-[16px] leading-relaxed text-black shadow-sm"><strong className="block text-primary">ResiliChain Copilot siap.</strong>Tanyakan dampak skenario, alasan pemilihan rute, pemasok terdampak, atau pesanan yang masih berisiko.</div>
          </article>}

          {messages.map(message => <article key={message.id} className={`flex items-start gap-4 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {message.role === "assistant" && <span className="grid size-14 shrink-0 place-items-center rounded-full bg-primary text-white shadow-md"><Bot className="size-7" /></span>}
            <div className={`max-w-[72%] rounded-[25px] px-6 py-4 text-[15px] leading-relaxed shadow-sm ${message.role === "user" ? "bg-primary text-white" : "bg-[#dedede] text-black"}`}>
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
              {message.provider && <p className="mt-3 text-[10px] font-semibold uppercase text-muted">{message.provider === "gemini" ? "Gemini - grounded" : message.provider === "qwen" ? "Qwen - grounded" : "Deterministic fallback - grounded"}</p>}
            </div>
            {message.role === "user" && <span className="grid size-14 shrink-0 place-items-center rounded-full bg-[#9d9d9d] text-white shadow-md"><UserRound className="size-7" /></span>}
          </article>)}
          {conversation.isSending && <div className="flex items-center gap-3 pl-[72px] text-sm text-muted"><span className="size-2 animate-pulse rounded-full bg-primary" /> Meninjau bukti simulasi...</div>}
          {ask.isError && <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft/70 p-3 text-sm text-danger">{ask.error.message}</div>}
        </div>

        <footer className="shrink-0 bg-white px-5 py-4 shadow-[0_-3px_18px_rgb(0_0_0/12%)] md:px-9">
          <div className="mb-3 flex flex-wrap gap-2">{visibleQuestions.map(question => <button key={question} type="button" onClick={() => void submit(question)} disabled={conversation.isSending} className="rounded-[20px] border border-[#9d9d9d] bg-white px-4 py-2 text-[12px] font-medium text-[#5a5a5a] transition hover:border-primary hover:text-primary disabled:opacity-50">{question}</button>)}</div>
          <form onSubmit={onSubmit} className="flex gap-3">
            <label htmlFor="copilot-message" className="sr-only">Ask ResiliChain Copilot</label>
            <input id="copilot-message" value={input} onChange={event => setInput(event.target.value)} maxLength={1_000} placeholder="Ketik pertanyaan Anda disini..." className="h-[62px] min-w-0 flex-1 rounded-[25px] border border-[#9d9d9d] bg-[#dbdbdb] px-5 text-[16px] text-black outline-none placeholder:text-[#5a5a5a] focus:border-primary" />
            <button type="submit" aria-label="Send" disabled={!input.trim() || conversation.isSending || simulation.data?.status !== "completed"} className="inline-flex h-[62px] min-w-[150px] items-center justify-center gap-3 rounded-[25px] bg-primary px-6 text-[22px] font-bold text-white hover:bg-primary-dark disabled:opacity-50"><span className="hidden sm:inline">Send</span><Send className="size-6" /></button>
          </form>
        </footer>
      </section>

      <aside className="bg-[linear-gradient(145deg,#eba92d_20%,#856019_150%)] p-5 xl:h-full xl:overflow-y-auto xl:overscroll-contain" aria-label="Konteks simulasi">
        <h2 className="sr-only">Current Simulation Context</h2>
        <div className="space-y-3">{contextItems.map(([label, value]) => <ContextItem key={label} label={label} value={value} />)}</div>
        <div className="mt-4 rounded-[20px] border border-white/50 bg-white/20 p-4 text-xs leading-relaxed text-white">Copilot hanya menjelaskan hasil ML, NetworkX, dan OR-Tools yang sudah dihitung. Copilot tidak mengubah rute, alokasi, prioritas, atau KPI.</div>
      </aside>
    </div>
  </AppShell>;
}

function ContextItem({ label, value }: { label: string; value: string }) {
  return <div className="min-h-[92px] rounded-[22px] bg-white px-5 py-4 text-primary shadow-sm"><div className="mb-1 text-[14px] font-bold">{label}</div><div className="text-[12px] leading-snug text-primary">{value}</div></div>;
}
