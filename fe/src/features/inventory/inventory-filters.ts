import type { InventoryLocale } from "@/components/providers/inventory-language-provider";
import { localizeInventoryTerm } from "@/lib/inventory-translations";

export function matchesMaterialName(name: string, query: string, locale: InventoryLocale) {
  return localizeInventoryTerm(name, locale).toLocaleLowerCase(locale).includes(query.trim().toLocaleLowerCase(locale));
}

export function movementBusinessDate(timestamp: string) {
  const parts = new Intl.DateTimeFormat("en", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(timestamp));
  const part = (type: string) => parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function matchesMovementDate(timestamp: string, from: string, to: string) {
  const date = movementBusinessDate(timestamp);
  return (!from || date >= from) && (!to || date <= to);
}
