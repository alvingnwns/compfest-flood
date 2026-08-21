import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RecoveryLoadingOverlay } from "./recovery-loading-overlay";

describe("RecoveryLoadingOverlay", () => {
  afterEach(() => vi.useRealTimers());

  it("communicates staged estimated progress while recovery is generated", () => {
    vi.useFakeTimers();
    render(<RecoveryLoadingOverlay />);

    expect(screen.getByRole("status", { name: "Menyusun rencana pemulihan" })).toHaveClass("fixed", "inset-0", "z-[70]");
    expect(screen.getByText("Tahap 1 dari 4")).toBeInTheDocument();
    expect(screen.getByText("Menganalisis kendala operasional")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "18");

    act(() => vi.advanceTimersByTime(700));

    expect(screen.getByText("Tahap 2 dari 4")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");
  });

  it("stops below completion while waiting for the backend response", () => {
    vi.useFakeTimers();
    render(<RecoveryLoadingOverlay />);

    act(() => vi.advanceTimersByTime(700));
    act(() => vi.advanceTimersByTime(700));
    act(() => vi.advanceTimersByTime(700));

    expect(screen.getByText("Tahap 4 dari 4")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "88");
  });
});
