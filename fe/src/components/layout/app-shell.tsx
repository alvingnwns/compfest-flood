"use client";

import { ChartNoAxesCombined, ChevronLeft, ChevronRight, Map, Menu, MessageCircleMore, RefreshCcw, Settings2, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import type { CSSProperties } from "react";

const items: Array<{ href: string; label: string; icon: LucideIcon }> = [
  { href: "/scenario", label: "Skenario", icon: Settings2 },
  { href: "/disruption", label: "Peta Gangguan", icon: Map },
  { href: "/recovery", label: "Rencana Pemulihan", icon: RefreshCcw },
  { href: "/impact", label: "Analisis Dampak", icon: ChartNoAxesCombined },
  { href: "/copilot", label: "ARUNA Copilot", icon: MessageCircleMore },
];

export function navigationTarget(href: string, simulation: string | null, condition: string | null): string {
  if (!simulation || href === "/scenario") return href;
  return `${href}?simulation=${encodeURIComponent(simulation)}${condition ? `&condition=${encodeURIComponent(condition)}` : ""}`;
}

export function AppShell({ children, title, actions }: { children: React.ReactNode; title?: string; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const params = useSearchParams();
  const simulation = params.get("simulation");
  const condition = params.get("condition");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebarW = collapsed ? "88px" : "260px";
  const shellStyle = { "--sidebar-width": sidebarW } as CSSProperties;

  const navLinks = (mobile = false) =>
    items.map(({ href, label, icon: Icon }) => {
      const active = pathname === href;
      const target = navigationTarget(href, simulation, condition);
      return (
        <Link
          key={href}
          href={target}
          aria-current={active ? "page" : undefined}
          title={!mobile && collapsed ? label : undefined}
          onClick={() => mobile && setMobileOpen(false)}
          className={`flex h-11 w-full items-center ${!mobile && collapsed ? "justify-center px-0" : "gap-3 px-3.5"} rounded-[12px] text-[15px] font-semibold transition duration-200 active:scale-[.98] ${active ? "bg-primary-dark text-[#ffc558]" : "text-white hover:bg-primary-dark/55"}`}
        >
          <Icon className="h-5 w-5 shrink-0" strokeWidth={2.1} aria-hidden="true" />
          {(mobile || !collapsed) && <span className="whitespace-nowrap">{label}</span>}
        </Link>
      );
    });

  return (
    <div className="min-h-screen bg-background text-ink" style={shellStyle}>
      {/* Sidebar */}
      <aside
        className="fixed inset-y-0 left-0 z-50 hidden w-[var(--sidebar-width)] flex-col overflow-hidden bg-primary transition-all duration-300 md:flex"
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
          {navLinks()}
        </nav>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            aria-label="Tutup navigasi"
            className="absolute inset-0 bg-black/45"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-[min(82vw,300px)] flex-col bg-primary shadow-2xl">
            <div className="flex h-20 items-center gap-3 bg-primary-dark px-4">
              <Image src="/logo-aruna.png" alt="ARUNA Logo" width={48} height={28} priority className="h-8 w-auto object-contain" />
              <span className="flex-1 text-xl font-bold tracking-wide text-white">ARUNA</span>
              <button type="button" aria-label="Tutup menu" onClick={() => setMobileOpen(false)} className="grid size-9 place-items-center rounded-lg text-white hover:bg-white/15">
                <X className="size-5" />
              </button>
            </div>
            <nav aria-label="Navigasi utama mobile" className="mt-6 flex-1 space-y-2 overflow-y-auto px-3">
              {navLinks(true)}
            </nav>
          </aside>
        </div>
      )}

      {/* Top header */}
      <header className="fixed left-0 right-0 top-0 z-40 flex h-20 items-center justify-between bg-white px-4 shadow-[0_2px_4px_rgb(0_0_0/25%)] transition-all duration-300 md:left-[var(--sidebar-width)] md:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <button type="button" aria-label="Buka menu navigasi" onClick={() => setMobileOpen(true)} className="grid size-10 shrink-0 place-items-center rounded-xl text-primary hover:bg-primary-soft md:hidden">
            <Menu className="size-6" />
          </button>
          <div className="min-w-0 truncate text-[22px] font-bold text-primary md:text-[32px]">{title ?? "ARUNA"}</div>
        </div>
        <div className="flex shrink-0 items-center gap-3">{actions}</div>
      </header>

      {/* Main content */}
      <main className="min-h-screen pt-20 transition-all duration-300 md:ml-[var(--sidebar-width)]">
        {children}
      </main>
    </div>
  );
}
