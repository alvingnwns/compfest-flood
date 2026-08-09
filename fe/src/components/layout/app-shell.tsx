"use client";

import { Activity, ChartNoAxesCombined, Factory, LayoutDashboard, Map, RotateCcw, Settings2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { LucideIcon } from "lucide-react";

const items: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/scenario", label: "Scenario", icon: Settings2 },
  { href: "/disruption", label: "Disruption Map", icon: Map },
  { href: "/recovery", label: "Recovery Plan", icon: RotateCcw },
  { href: "/impact", label: "Impact Analysis", icon: ChartNoAxesCombined },
];

export function AppShell({ children, title, actions }: { children: React.ReactNode; title?: string; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const simulation = params.get("simulation");

  return <div className="min-h-screen bg-background text-ink">
    <aside className="fixed inset-y-0 left-0 z-50 hidden w-60 flex-col border-r border-outline bg-surface px-4 py-6 shadow-sm md:flex">
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-white"><Factory size={19} /></div>
        <div><div className="text-lg font-semibold leading-tight text-primary">ResiliChain AI</div><div className="mono text-[10px] uppercase tracking-wider text-muted">Supply Chain Control</div></div>
      </div>
      <nav aria-label="Primary navigation" className="flex-1 space-y-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          const target = simulation && href !== "/scenario" && href !== "/overview" ? `${href}?simulation=${simulation}` : href;
          return <Link key={href} href={target} aria-current={active ? "page" : undefined} className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition duration-200 active:scale-[.98] ${active ? "bg-secondary-soft/70 font-semibold text-primary" : "text-muted hover:bg-surface-high"}`}><Icon size={19} aria-hidden="true" /><span>{label}</span></Link>;
        })}
      </nav>
      <div className="flex items-center justify-center gap-2 rounded-lg border border-outline bg-surface-low px-3 py-2 text-xs font-semibold text-muted"><Activity size={16} /> Demo Environment</div>
    </aside>
    <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between border-b border-outline bg-surface/95 px-4 backdrop-blur md:left-60 md:px-8">
      <div className="min-w-0"><div className="truncate text-sm font-semibold text-primary md:text-lg">{title ?? "Historical Replay · Jakarta · 04 Mar 2025"}</div><div className="mono hidden text-[10px] text-muted sm:block">Historical Replay · Jakarta · 04 Mar 2025</div></div>
      <div className="flex items-center gap-2">{actions}<span className="hidden rounded-full border border-outline bg-surface-low px-3 py-1.5 text-xs font-medium text-muted lg:inline">Historical Data Loaded</span></div>
    </header>
    <main className="min-h-screen pt-16 md:ml-60">{children}</main>
  </div>;
}
