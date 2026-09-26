import { z, type ZodType } from "zod";
import { publicEnv } from "@/config/public-env";

const envelope = z.object({ error: z.object({ code: z.string(), message: z.string(), details: z.unknown().nullable().optional() }) });
export class InventoryApiError extends Error {
  constructor(public readonly status: number, public readonly code: string, message: string, public readonly details?: unknown) { super(message); this.name = "InventoryApiError"; }
}
export const usesInventoryApi = () => publicEnv.NEXT_PUBLIC_DATA_SOURCE === "api";
export async function inventoryRequest<T>(path: string, schema: ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${publicEnv.NEXT_PUBLIC_API_BASE_URL}/api${path}`, { ...init, headers: { Accept: "application/json", "Content-Type": "application/json", ...init?.headers } });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const parsed = envelope.safeParse(body);
    throw new InventoryApiError(response.status, parsed.success ? parsed.data.error.code : "REQUEST_FAILED", parsed.success ? parsed.data.error.message : "Request failed.", parsed.success ? parsed.data.error.details : undefined);
  }
  return schema.parse(body);
}
export function wibDate(value = new Date()) { return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit" }).format(value); }
export const mutationHeaders = (key: string) => ({ "Idempotency-Key": key });
