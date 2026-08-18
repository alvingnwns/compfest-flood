import type { ZodType } from "zod";
import { publicEnv } from "@/config/public-env";
import { apiErrorSchema, type ApiErrorPayload } from "@/domain/common";

const userFacingErrors: Record<string, string> = {
  UNKNOWN_ANALYSIS_MODE: "Mode analisis tidak dikenali. Pilih kembali mode analisis.",
  UNSUPPORTED_REGION: "Wilayah tersebut belum didukung. Saat ini simulasi tersedia untuk Jakarta.",
  UNKNOWN_RAINFALL_SCENARIO: "Pola curah hujan tidak dikenali. Pilih kembali pola yang tersedia.",
  DYNAMIC_HAZARD_RUNTIME_ERROR: "Model hazard temporal sedang tidak tersedia. Coba lagi atau gunakan Pemutaran Ulang Historis.",
  TEMPORAL_MODEL_INPUT_INVALID: "Data pola hujan tidak dapat diproses oleh model temporal.",
  BUSINESS_DATA_VALIDATION_FAILED: "Workbook berisi data yang belum valid. Periksa detail lalu unggah kembali.",
  BUSINESS_SNAPSHOT_NOT_FOUND: "Snapshot bisnis tidak ditemukan atau sudah kedaluwarsa. Unggah workbook kembali.",
  UNSUPPORTED_FILE_TYPE: "Unggah workbook Excel tanpa macro dengan format .xlsx.",
  FILE_TOO_LARGE: "Ukuran workbook melebihi batas 5 MB.",
  simulation_not_ready: "Simulasi masih diproses. Tunggu sejenak lalu coba lagi.",
  disruption_not_ready: "Analisis gangguan belum tersedia. Tunggu simulasi selesai lalu coba lagi.",
  recovery_not_ready: "Rencana pemulihan belum tersedia untuk simulasi ini.",
};

export function userFacingApiMessage(payload: ApiErrorPayload): string {
  return userFacingErrors[payload.code] ?? payload.message;
}

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly payload: ApiErrorPayload) { super(userFacingApiMessage(payload)); this.name = "ApiError"; }
  get code() { return this.payload.code; }
  get retryable() { return this.payload.retryable; }
  get details() { return this.payload.details; }
}

export async function apiRequest<T>(path: string, schema: ZodType<T>, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${publicEnv.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(!isFormData ? { "Content-Type": "application/json" } : {}),
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const parsed = apiErrorSchema.safeParse(await response.json().catch(() => null));
    const fallback: ApiErrorPayload = { code: "unexpected_api_error", message: "Permintaan tidak dapat diselesaikan.", retryable: response.status >= 500 };
    throw new ApiError(response.status, parsed.success ? parsed.data : fallback);
  }
  return schema.parse(await response.json());
}

export const apiUrl = (path: string) => `${publicEnv.NEXT_PUBLIC_API_BASE_URL}${path}`;
