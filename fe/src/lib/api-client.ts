import type { ZodType } from "zod";
import { publicEnv } from "@/config/public-env";
import { apiErrorSchema, type ApiErrorPayload } from "@/domain/common";

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly payload: ApiErrorPayload) { super(payload.message); this.name = "ApiError"; }
  get code() { return this.payload.code; }
  get retryable() { return this.payload.retryable; }
  get details() { return this.payload.details; }
}

export async function apiRequest<T>(path: string, schema: ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${publicEnv.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...init, headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const parsed = apiErrorSchema.safeParse(await response.json().catch(() => null));
    const fallback: ApiErrorPayload = { code: "unexpected_api_error", message: "The request could not be completed.", retryable: response.status >= 500 };
    throw new ApiError(response.status, parsed.success ? parsed.data : fallback);
  }
  return schema.parse(await response.json());
}
