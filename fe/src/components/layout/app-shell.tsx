"use client";

import { ChartNoAxesCombined, ChevronLeft, ChevronRight, LayoutDashboard, Map, MessageCircleMore, RefreshCcw, Settings2 } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";

const items: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/overview", label: "Ringkasan", icon: LayoutDashboard },
  { href: "/scenario", label: "Skenario", icon: Settings2 },
  { href: "/disruption", label: "Peta Gangguan", icon: Map },
  { href: "/recovery", label: "Rencana Pemulihan", icon: RefreshCcw },
  { href: "/impact", label: "Analisis Dampak", icon: ChartNoAxesCombined },
  { href: "/copilot", label: "ARUNA Copilot", icon: MessageCircleMore },
];

export function AppShell({ children, title, actions }: { children: React.ReactNode; title?: string; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const simulation = params.get("simulation");
  const [collapsed, setCollapsed] = useState(false);

  const sidebarW = collapsed ? "88px" : "260px";

  return (
    <div className="min-h-screen bg-background text-ink">
      {/* Sidebar */}
      <aside
        className="fixed inset-y-0 left-0 z-50 hidden flex-col bg-primary md:flex overflow-hidden transition-all duration-300"
        style={{ width: sidebarW }}
      >
        {/* Header — contains logo and collapse toggle */}
        <div className={`flex h-20 shrink-0 items-center bg-primary-dark ${collapsed ? "justify-between px-3 gap-1.5" : "px-3 gap-2"}`}>
          <div className="flex h-10 w-10 shrink-0 items-center justify-center">
            <Image
              src="/logo-aruna.png"
              alt="ARUNA Logo"
              width={48}
              height={28}
              priority
              className="h-8 w-auto object-contain drop-shadow-sm"
            />
          </div>
          {!collapsed && (
            <div className="ml-1 flex-1 whitespace-nowrap text-[20px] font-bold tracking-wide text-white [text-shadow:0_0_8px_rgb(0_0_0/25%)]">
              ARUNA
            </div>
          )}
          {/* Collapse toggle button */}
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Buka sidebar" : "Tutup sidebar"}
            className="grid size-8 shrink-0 place-items-center rounded-[8px] text-white/80 transition hover:bg-white/15 hover:text-white"
          >
            {collapsed ? <ChevronRight className="size-5" /> : <ChevronLeft className="size-5" />}
          </button>
        </div>

        {/* Nav items */}
        <nav aria-label="Navigasi utama" className="mt-8 flex-1 space-y-2 px-3 overflow-hidden">
          {items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            const condition = params.get("condition");
            const target =
              simulation && href !== "/scenario" && href !== "/overview"
                ? `${href}?simulation=${simulation}${condition ? `&condition=${encodeURIComponent(condition)}` : ""}`
                : href;
            return (
              <Link
                key={href}
                href={target}
                aria-current={active ? "page" : undefined}
                title={collapsed ? label : undefined}
                className={`flex h-11 w-full items-center ${collapsed ? "justify-center px-0" : "gap-3 px-3.5"} rounded-[12px] text-[15px] font-semibold transition duration-200 active:scale-[.98] ${active ? "bg-primary-dark text-[#ffc558]" : "text-white hover:bg-primary-dark/55"}`}
              >
                <Icon className="h-5 w-5 shrink-0" strokeWidth={2.1} aria-hidden="true" />
                {!collapsed && <span className="whitespace-nowrap">{label}</span>}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Top header */}
      <header
        className="fixed top-0 right-0 z-40 flex h-20 items-center justify-between bg-white px-5 shadow-[0_2px_4px_rgb(0_0_0/25%)] md:h-20 md:px-8 transition-all duration-300"
        style={{ left: sidebarW }}
      >
        <div className="min-w-0 truncate text-[24px] font-bold text-primary md:text-[32px]">{title ?? "Ringkasan"}</div>
        <div className="flex shrink-0 items-center gap-3">{actions}</div>
      </header>

      {/* Main content */}
      <main
        className="min-h-screen pt-20 transition-all duration-300"
        style={{ marginLeft: sidebarW }}
      >
        {children}
      </main>
    </div>
  );
}
