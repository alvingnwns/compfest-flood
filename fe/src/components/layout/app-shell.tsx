"use client";

import { ChartNoAxesCombined, LayoutDashboard, Map, MessageCircleMore, RefreshCcw, Settings2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { LucideIcon } from "lucide-react";

const items: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/overview", label: "Ringkasan", icon: LayoutDashboard },
  { href: "/scenario", label: "Skenario", icon: Settings2 },
  { href: "/disruption", label: "Peta Gangguan", icon: Map },
  { href: "/recovery", label: "Rencana Pemulihan", icon: RefreshCcw },
  { href: "/impact", label: "Analisis Dampak", icon: ChartNoAxesCombined },
  { href: "/copilot", label: "ResiliChain Copilot", icon: MessageCircleMore },
];

export function AppShell({ children, title, actions }: { children: React.ReactNode; title?: string; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const simulation = params.get("simulation");

  return <div className="min-h-screen bg-background text-ink">
    <aside className="fixed inset-y-0 left-0 z-50 hidden w-[315px] flex-col bg-primary px-[29px] md:flex">
      <div className="-mx-[29px] flex h-[125px] items-center rounded-b-[50px] bg-primary-dark px-[29px]">
        <div className="h-[53px] w-[50px] rounded-[14px] bg-secondary-soft" aria-hidden="true" />
        <div className="ml-3 whitespace-nowrap text-[24px] font-semibold text-white [text-shadow:0_0_10px_rgb(0_0_0/25%)]">ResiliChain AI</div>
      </div>
      <nav aria-label="Navigasi utama" className="mt-10 flex-1 space-y-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          const target = simulation && href !== "/scenario" && href !== "/overview" ? `${href}?simulation=${simulation}` : href;
          return <Link key={href} href={target} aria-current={active ? "page" : undefined} className={`-mx-[14px] flex h-[50px] w-[285px] items-center gap-[10px] rounded-[15px] px-[14px] text-[20px] font-semibold text-white transition duration-200 active:scale-[.98] ${active ? "bg-primary-dark text-[#ffc558]" : "hover:bg-primary-dark/55"}`}><Icon className="h-[37px] w-[37px] shrink-0" strokeWidth={2.1} aria-hidden="true" /><span className="whitespace-nowrap">{label}</span></Link>;
        })}
      </nav>
    </aside>
    <header className="fixed inset-x-0 top-0 z-40 flex h-20 items-center justify-between bg-white px-5 shadow-[0_2px_4px_rgb(0_0_0/25%)] md:left-[315px] md:h-[125px] md:px-[65px]">
      <div className="min-w-0 truncate text-[30px] font-extrabold text-primary md:text-[64px] md:leading-none">{title ?? "Ringkasan"}</div>
      <div className="flex shrink-0 items-center gap-3">{actions}</div>
    </header>
    <main className="min-h-screen pt-20 md:ml-[315px] md:pt-[125px]">{children}</main>
  </div>;
}
