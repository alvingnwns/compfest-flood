"use client";

import { ArrowRight, Bot, Send, ShieldCheck, Trash2, UserRound } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { operationalConditionLabel } from "@/components/simulation/scenario-context-card";
import { ErrorState, FullPageState, LoadingState } from "@/components/ui/states";
import { getRainfallScenario } from "@/features/scenario/scenario-presets";
import { useCopilotConversation } from "./copilot-conversation-store";
import { toRecentCopilotMessages } from "./copilot-session";
import { useAskCopilot, useDisruptionAnalysis, useImpactComparison, useRecoveryPlan, useScenario, useSimulation } from "@/hooks/use-aruna-data";
import { formatCompactIdr, formatRisk } from "@/lib/format";

const initialQuestions = [
  "Apa dampaknya kalau kondisi ini memburuk?",
  "Kalau satu kendaraan tidak tersedia, apa yang bisa terjadi?",
  "Supplier mana yang paling terdampak?",
  "Pesanan mana yang masih beresiko?",
  "Kenapa rute ini dipilih?",
];

const questionTranslations: Record<string, string> = {
  "Which supplier is most affected?": "Supplier mana yang paling terdampak?",
  "What is the biggest bottleneck?": "Di mana hambatan operasional terbesar?",
  "Why was this route chosen?": "Kenapa rute ini dipilih?",
  "What are the risk-aware candidate routes?": "Apa saja rute alternatif yang aman?",
  "Why was this recovery plan selected?": "Mengapa rencana pemulihan ini dipilih?",
  "What trade-offs does this plan make?": "Apa penyesuaian dari rencana ini?",
  "Which orders remain at risk?": "Pesanan mana yang masih beresiko?",
  "How did the recovery plan change sales exposure?": "Bagaimana rencana pemulihan menurunkan risiko penjualan?",
};

function translateQuestion(question: string): string {
  return questionTranslations[question] ?? question;
}

function ModelStatusBadge({ provider }: { provider?: string }) {
  const isAi = provider === "gemini" || provider === "qwen";

  if (isAi) {
    const modelName = provider === "gemini" ? "Gemini AI" : "Qwen AI";
    return (
      <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1.5 text-[12px] font-semibold text-emerald-800 shadow-sm">
        <span className="relative flex size-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex size-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.9)]" />
        </span>
        <span>{modelName} Aktif (Grounded)</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/15 px-3.5 py-1.5 text-[12px] font-semibold text-amber-900 shadow-sm">
      <span className="relative flex size-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex size-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.9)]" />
      </span>
      <span>Deterministic Fallback (Grounded)</span>
    </div>
  );
}

export function CopilotPage() {
  const params = useSearchParams();
  const simulationId = params.get("simulation") ?? "";
  const condition = params.get("condition") ?? "normal";
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
  const rawQuestions = suggestedQuestions.length > 0 ? suggestedQuestions : messages.length === 0 ? initialQuestions : [];
  const visibleQuestions = rawQuestions.map(translateQuestion);

  const recoveryData = recovery.data && "summary" in recovery.data ? recovery.data : undefined;
  const logisticsAction = recoveryData?.logisticsActions[0];
  const fulfilledMetric = impact.data?.metrics.find(metric => metric.key === "orders-fulfilled");
  const failedMetric = impact.data?.metrics.find(metric => metric.key === "failed-orders");
  const salesMetric = impact.data?.metrics.find(metric => metric.key === "sales-exposure-risk");
  const overallRisk = useMemo(() => {
    const ranking = { low: 0, medium: 1, high: 2, critical: 3 } as const;
    return disruption.data?.roads.reduce<"low" | "medium" | "high" | "critical">((highest, road) => ranking[road.riskLevel] > ranking[highest] ? road.riskLevel : highest, "low");
  }, [disruption.data]);

  const latestAssistantMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].provider) {
        return messages[i];
      }
    }
    return undefined;
  }, [messages]);

  const activeProvider = latestAssistantMessage?.provider ?? "deterministic";

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
      conversation.setSuggestions(response.suggestedQuestions.map(translateQuestion));
    } finally {
      conversation.setSending(false);
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submit(input);
  };

  if (!simulationId) return (
    <AppShell title="ARUNA Copilot">
      <FullPageState>
        <section className="card mx-auto w-full max-w-lg p-8 text-center">
          <ShieldCheck className="mx-auto mb-4 text-primary" size={36} />
          <h1 className="mb-2 text-xl font-semibold">Jalankan simulasi terlebih dahulu</h1>
          <p className="mb-6 max-w-lg text-sm text-muted">Jalankan simulasi skenario sebelum membuka ARUNA Copilot agar konteks operasional tersedia.</p>
          <Link href="/scenario" className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white">Buka Skenario <ArrowRight size={17} /></Link>
        </section>
      </FullPageState>
    </AppShell>
  );

  if (simulation.isLoading) return <AppShell title="ARUNA Copilot"><LoadingState label="Memuat konteks simulasi..." /></AppShell>;
  if (simulation.isError) return <AppShell title="ARUNA Copilot"><ErrorState message={simulation.error.message} onRetry={() => void simulation.refetch()} /></AppShell>;
  if (!conversation.hydrated) return <AppShell title="ARUNA Copilot"><LoadingState label="Memulihkan percakapan..." /></AppShell>;

  const dynamic = simulation.data?.analysisMode === "scenario-simulation" && simulation.data?.hazard !== undefined;
  const rainfall = dynamic ? getRainfallScenario(simulation.data?.hazard?.rainfallScenario) : undefined;
  const scenarioTitle = dynamic ? `${rainfall?.label ?? "Pola Hujan"} (Simulasi Kondisi)` : (scenario.data?.name ?? "Banjir Jakarta — 04 Mar 2025");
  const businessDataSourceLabel = simulation.data?.businessDataSource === "custom" ? "Unggahan Sendiri (Kustom)" : "Data Standar Demo";
  const conditionLabel = operationalConditionLabel(condition);
  const logisticsAssignmentLabel = logisticsAction
    ? `${logisticsAction.originalWarehouseName ?? "Belum teralokasi"} → ${logisticsAction.recoveryWarehouseName}`
    : "Sesuai rencana pemulihan";

  const contextItems = [
    ["Skenario", scenarioTitle],
    ["Data Bisnis", businessDataSourceLabel],
    ["Kondisi Operasional", conditionLabel],
    ["Resiko jalan keseluruhan", overallRisk ? formatRisk(overallRisk) : "Sedang"],
    ["Pihak terdampak", disruption.data ? `${disruption.data.impact.impactedSupplierIds.length} pemasok dan ${disruption.data.impact.impactedWarehouseIds.length} gudang` : "Memuat..."],
    ["Rute pemulihan", logisticsAssignmentLabel],
    ["Pesanan terpenuhi", fulfilledMetric ? `${fulfilledMetric.recovery}/${fulfilledMetric.total}` : recoveryData ? `${recoveryData.summary.recoverableOrders}/${recoveryData.summary.totalOrders}` : "Memuat..."],
    ["Pesanan gagal", failedMetric ? `${failedMetric.recovery} pesanan` : recoveryData ? `${recoveryData.summary.totalOrders - recoveryData.summary.recoverableOrders} pesanan` : "0 pesanan"],
    ["Penjualan terdampak", salesMetric ? formatCompactIdr(salesMetric.recovery) : disruption.data ? formatCompactIdr(disruption.data.impact.salesExposure.amount) : "Rp 0"],
  ];

  return (
    <AppShell title="ARUNA Copilot" actions={<ModelStatusBadge provider={activeProvider} />}>
      <div className="copilot-pattern grid min-h-[calc(100vh-80px)] xl:h-[calc(100vh-80px)] xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_370px] xl:overflow-hidden">
        <section className="relative flex min-h-[720px] flex-col overflow-hidden border-r border-outline xl:min-h-0">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={conversation.clear}
              disabled={conversation.isSending}
              aria-label="Hapus percakapan"
              title="Hapus percakapan"
              className="absolute left-5 top-5 z-20 grid size-10 place-items-center rounded-full border border-outline bg-white/90 text-muted shadow-sm hover:text-danger disabled:opacity-50"
            >
              <Trash2 className="size-4" />
            </button>
          )}

          <div ref={messageViewport} className="flex-1 space-y-6 overflow-y-auto px-6 py-8 md:px-12">
            {messages.length === 0 && (
              <article className="mx-auto mt-4 flex max-w-[780px] items-start gap-4">
                <span className="grid size-14 shrink-0 place-items-center rounded-full bg-primary text-white shadow-md">
                  <Bot className="size-7" />
                </span>
                <div className="rounded-[25px] bg-[#dedede] px-7 py-6 text-[16px] leading-relaxed text-black shadow-sm">
                  <strong className="block text-primary">ARUNA Copilot siap.</strong>
                  Tanyakan dampak skenario, alasan pemilihan rute, pemasok terdampak, atau pesanan yang masih berisiko.
                </div>
              </article>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={`flex items-start gap-4 ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" && (
                  <span className="grid size-14 shrink-0 place-items-center rounded-full bg-primary text-white shadow-md">
                    <Bot className="size-7" />
                  </span>
                )}
                <div
                  className={`max-w-[72%] rounded-[25px] px-6 py-4 text-[15px] leading-relaxed shadow-sm ${message.role === "user" ? "bg-primary text-white" : "bg-[#dedede] text-black"
                    }`}
                >
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                </div>
                {message.role === "user" && (
                  <span className="grid size-14 shrink-0 place-items-center rounded-full bg-[#9d9d9d] text-white shadow-md">
                    <UserRound className="size-7" />
                  </span>
                )}
              </article>
            ))}
            {conversation.isSending && (
              <div className="flex items-center gap-3 pl-[72px] text-sm text-muted">
                <span className="size-2 animate-pulse rounded-full bg-primary" /> Meninjau bukti simulasi...
              </div>
            )}
            {ask.isError && (
              <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft/70 p-3 text-sm text-danger">
                {ask.error.message}
              </div>
            )}
          </div>

          <footer className="shrink-0 bg-white px-5 py-4 shadow-[0_-3px_18px_rgb(0_0_0/12%)] md:px-9">
            <div className="mb-3 flex flex-wrap gap-2">
              {visibleQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => void submit(question)}
                  disabled={conversation.isSending}
                  className="rounded-[20px] border border-[#9d9d9d] bg-white px-4 py-2 text-[12px] font-medium text-[#5a5a5a] transition hover:border-primary hover:text-primary disabled:opacity-50"
                >
                  {question}
                </button>
              ))}
            </div>
            <form onSubmit={onSubmit} className="flex gap-3">
              <label htmlFor="copilot-message" className="sr-only">Tanyakan ARUNA Copilot</label>
              <input
                id="copilot-message"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                maxLength={1_000}
                placeholder="Ketik pertanyaan Anda disini..."
                className="h-[62px] min-w-0 flex-1 rounded-[25px] border border-[#9d9d9d] bg-white px-5 text-[16px] text-black outline-none placeholder:text-[#5a5a5a] focus:border-primary shadow-sm"
              />
              <button
                type="submit"
                aria-label="Kirim"
                disabled={!input.trim() || conversation.isSending || simulation.data?.status !== "completed"}
                className="inline-flex h-[62px] min-w-[150px] items-center justify-center gap-3 rounded-[25px] bg-primary px-6 text-[22px] font-bold text-white hover:bg-primary-dark disabled:opacity-50"
              >
                <span className="hidden sm:inline">Send</span>
                <Send className="size-6" />
              </button>
            </form>
          </footer>
        </section>

        <aside className="bg-[linear-gradient(145deg,#eba92d_20%,#856019_150%)] p-5 xl:h-full xl:overflow-y-auto xl:overscroll-contain" aria-label="Konteks simulasi">
          <h2 className="sr-only">Konteks Simulasi Saat Ini</h2>
          <div className="space-y-3">
            {contextItems.map(([label, value]) => (
              <ContextItem key={label} label={label} value={value} />
            ))}
          </div>
          <div className="mt-4 rounded-[20px] border border-white/50 bg-white/20 p-4 text-xs leading-relaxed text-white">
            Copilot hanya menjelaskan hasil ML, NetworkX, dan OR-Tools yang sudah dihitung. Copilot tidak mengubah rute, alokasi, prioritas, atau KPI.
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

function ContextItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-h-[92px] rounded-[22px] bg-white px-5 py-4 text-primary shadow-sm">
      <div className="mb-1 text-[14px] font-bold">{label}</div>
      <div className="text-[12px] leading-snug text-primary">{value}</div>
    </div>
  );
}
