"use client";

import { Check, Network } from "lucide-react";
import { useEffect, useState } from "react";

const progressSteps = [
  { label: "Menganalisis kendala operasional", progress: 18 },
  { label: "Mengevaluasi kandidat rute", progress: 42 },
  { label: "Mengoptimalkan rencana pemulihan", progress: 68 },
  { label: "Menyiapkan hasil pemulihan", progress: 88 },
] as const;

export function RecoveryLoadingOverlay() {
  const [step, setStep] = useState(0);
  const current = progressSteps[step];

  useEffect(() => {
    if (step >= progressSteps.length - 1) return;
    const timer = window.setTimeout(() => setStep((value) => value + 1), 700);
    return () => window.clearTimeout(timer);
  }, [step]);

  return (
    <div
      className="fixed inset-0 z-[70] grid place-items-center bg-[#edf2f2]/80 p-4 backdrop-blur-[3px]"
      role="status"
      aria-live="polite"
      aria-label="Menyusun rencana pemulihan"
    >
      <section className="w-full max-w-[440px] overflow-hidden rounded-[32px] border border-white/80 bg-white shadow-[0_20px_60px_rgb(41_64_91/28%)]">
        <div className="bg-primary px-7 pb-6 pt-7 text-center text-white">
          <span className="mx-auto grid size-14 place-items-center rounded-full bg-white/15 ring-1 ring-white/25">
            <Network className="size-7 animate-pulse" aria-hidden="true" />
          </span>
          <h2 className="mt-4 text-[21px] font-bold">Menyusun Rencana Pemulihan</h2>
          <p className="mt-1 text-[12px] text-white/75">ARUNA sedang menghitung rencana yang paling layak.</p>
        </div>

        <div className="px-7 py-6">
          <div className="flex items-center justify-between gap-4 text-[11px] font-semibold uppercase tracking-wide text-muted">
            <span>Estimasi progres</span>
            <span>Tahap {step + 1} dari {progressSteps.length}</span>
          </div>
          <div
            className="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-high"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={current.progress}
            aria-valuetext={current.label}
          >
            <div
              className="h-full rounded-full bg-[linear-gradient(90deg,#eba92d,#ffc558)] transition-[width] duration-500 ease-out"
              style={{ width: `${current.progress}%` }}
            />
          </div>

          <ol className="mt-6 space-y-3">
            {progressSteps.map((item, index) => {
              const complete = index < step;
              const active = index === step;
              return (
                <li
                  key={item.label}
                  className={`flex items-center gap-3 text-[13px] transition-colors ${active ? "font-bold text-primary-dark" : complete ? "font-semibold text-primary" : "text-muted/65"}`}
                >
                  <span
                    className={`grid size-6 shrink-0 place-items-center rounded-full text-[11px] ${active ? "bg-accent text-primary-dark ring-4 ring-accent/20" : complete ? "bg-primary text-white" : "bg-surface-high text-muted"}`}
                    aria-hidden="true"
                  >
                    {complete ? <Check className="size-3.5" strokeWidth={3} /> : index + 1}
                  </span>
                  {item.label}
                </li>
              );
            })}
          </ol>

          <p className="mt-6 text-center text-[11px] text-muted">Mohon tunggu, proses ini biasanya selesai dalam beberapa detik.</p>
        </div>
      </section>
    </div>
  );
}
