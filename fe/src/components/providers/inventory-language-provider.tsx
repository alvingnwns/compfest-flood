"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type InventoryLocale = "en" | "id";

type LanguageContextValue = {
  locale: InventoryLocale;
  setLocale: (locale: InventoryLocale) => void;
  toggleLocale: () => void;
};

const LanguageContext = createContext<LanguageContextValue>({
  locale: "en",
  setLocale: () => undefined,
  toggleLocale: () => undefined,
});
const storageKey = "aruna-inventory-language";

export function InventoryLanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<InventoryLocale>("en");

  useEffect(() => {
    const saved = window.localStorage.getItem(storageKey);
    if (saved !== "en" && saved !== "id") return;
    const timer = window.setTimeout(() => setLocale(saved), 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(storageKey, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo(() => ({
    locale,
    setLocale,
    toggleLocale: () => setLocale((current) => current === "en" ? "id" : "en"),
  }), [locale]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useInventoryLanguage() {
  return useContext(LanguageContext);
}
