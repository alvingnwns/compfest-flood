import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ErrorState, LoadingState } from "./states";

describe("analysis states", () => {
  it("announces loading copy", () => {
    render(<LoadingState label="Menghitung risiko relatif…" />);
    expect(screen.getByText("Menghitung risiko relatif…")).toBeInTheDocument();
  });

  it("offers a single retry action", async () => {
    const retry = vi.fn();
    render(<ErrorState message="Model sedang tidak tersedia." onRetry={retry} />);
    await userEvent.click(screen.getByRole("button", { name: "Coba Lagi" }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getAllByRole("button", { name: "Coba Lagi" })).toHaveLength(1);
  });
});
