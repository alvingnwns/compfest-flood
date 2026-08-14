import { describe, expect, it } from "vitest";
import { ApiError, userFacingApiMessage } from "./api-client";

describe("user-facing API errors", () => {
  it("maps dynamic runtime failures without exposing internal details", () => {
    const payload = { code: "DYNAMIC_HAZARD_RUNTIME_ERROR", message: "internal model path failed", retryable: true };
    expect(userFacingApiMessage(payload)).toMatch(/model hazard temporal/i);
    expect(new ApiError(500, payload).message).not.toContain("internal model path");
  });

  it("preserves safe backend messages for unknown error codes", () => {
    expect(userFacingApiMessage({ code: "safe_error", message: "Layanan belum tersedia.", retryable: true })).toBe("Layanan belum tersedia.");
  });
});
