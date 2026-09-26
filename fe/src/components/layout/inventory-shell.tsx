"use client";

import {
  Boxes,
  ChartNoAxesCombined,
  Gauge,
  Languages,
  Menu,
  MessageSquareMore,
  PackageSearch,
  Route,
  ShieldAlert,
  X,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
import { useInventoryLanguage } from "@/components/providers/inventory-language-provider";
import styles from "./inventory-shell.module.css";
import theme from "@/components/inventory/aruna-theme.module.css";

type NavItem = { label: { en: string; id: string }; icon: LucideIcon; href?: string };

const operationalItems: NavItem[] = [
  { label: { en: "Overview", id: "Ringkasan" }, icon: Gauge, href: "/ringkasan" },
  { label: { en: "Sales", id: "Penjualan" }, icon: ChartNoAxesCombined, href: "/penjualan" },
  { label: { en: "Inventory", id: "Gudang" }, icon: PackageSearch, href: "/gudang" },
];

const planningItems: NavItem[] = [
  { label: { en: "Demand Forecast", id: "Prediksi Permintaan" }, icon: Boxes, href: "/prediksi-permintaan" },
  { label: { en: "Stock Risks", id: "Stok Berisiko" }, icon: ShieldAlert, href: "/stok-berisiko" },
  { label: { en: "Optimization Plan", id: "Rencana Optimasi" }, icon: Route, href: "/rencana-optimasi" },
];

const utilityItems: NavItem[] = [
  { label: { en: "POS Simulator", id: "POS Simulator" }, icon: MessageSquareMore, href: "/pos-simulator" },
];

function NavigationGroup({ label, items, pathname, locale, onNavigate }: { label?: string; items: NavItem[]; pathname: string; locale: "en" | "id"; onNavigate?: () => void }) {
  return (
    <div className={styles.navGroup}>
      {label && <p className={styles.navLabel}>{label}</p>}
      <div className={styles.navList}>
        {items.map(({ label: labels, icon: Icon, href }) => {
          const itemLabel = labels[locale];
          const active = href === pathname;
          const content = (
            <>
              <Icon aria-hidden="true" className={styles.navIcon} strokeWidth={2.2} />
              <span>{itemLabel}</span>
            </>
          );

          return href ? (
            <Link key={itemLabel} href={href} aria-current={active ? "page" : undefined} className={`${styles.navItem} ${active ? styles.active : ""}`} onClick={onNavigate}>
              {content}
            </Link>
          ) : (
            <span key={itemLabel} aria-disabled="true" className={styles.navItem} title={locale === "en" ? "Page not available yet" : "Halaman belum tersedia"}>
              {content}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function Sidebar({ pathname, locale, onNavigate }: { pathname: string; locale: "en" | "id"; onNavigate?: () => void }) {
  return (
    <>
      <Link href="/" className={styles.brand} onClick={onNavigate} aria-label={locale === "en" ? "Go to landing page" : "Ke halaman utama"}>
        <Image src="/logo-aruna.png" alt="" width={78} height={44} priority className={styles.logo} />
        <span>Aruna AI</span>
      </Link>
      <nav aria-label="Navigasi ARUNA Inventory" className={styles.navigation}>
        <NavigationGroup label={locale === "en" ? "OPERATIONS" : "OPERASIONAL"} items={operationalItems} pathname={pathname} locale={locale} onNavigate={onNavigate} />
        <NavigationGroup label={locale === "en" ? "PLANNING" : "PERENCANAAN"} items={planningItems} pathname={pathname} locale={locale} onNavigate={onNavigate} />
        <div className={styles.navBottom}>
          <NavigationGroup items={utilityItems} pathname={pathname} locale={locale} onNavigate={onNavigate} />
        </div>
      </nav>
    </>
  );
}

export function InventoryShell({ children, title, actions }: { children: React.ReactNode; title: string; actions?: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { locale, toggleLocale } = useInventoryLanguage();

  return (
    <div className={`${theme.theme} ${styles.shell}`}>
      <aside className={styles.sidebar}><Sidebar pathname={pathname} locale={locale} /></aside>
      {mobileOpen && (
        <div className={styles.mobileLayer}>
          <button type="button" className={styles.backdrop} aria-label="Tutup navigasi" onClick={() => setMobileOpen(false)} />
          <aside className={styles.mobileSidebar}>
            <button type="button" className={styles.closeButton} aria-label="Tutup menu" onClick={() => setMobileOpen(false)}><X /></button>
            <Sidebar pathname={pathname} locale={locale} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}
      <header className={styles.header}>
        <button type="button" className={styles.menuButton} aria-label="Buka menu navigasi" onClick={() => setMobileOpen(true)}><Menu /></button>
        <h1>{title}</h1>
        <div className={styles.headerActions}>
          {actions}
          <button type="button" className={styles.languageButton} onClick={toggleLocale} aria-label={locale === "en" ? "Switch to Bahasa Indonesia" : "Ganti ke English"} title={locale === "en" ? "Bahasa Indonesia" : "English"}>
            <Languages aria-hidden="true" /><span>{locale === "en" ? "ID" : "EN"}</span>
          </button>
        </div>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
