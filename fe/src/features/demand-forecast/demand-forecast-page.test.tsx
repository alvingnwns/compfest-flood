import { vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DemandForecastPage } from "./demand-forecast-page";

describe("DemandForecastPage", () => {
  it("renders forecast controls, chart, and material requirements", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><DemandForecastPage /></QueryClientProvider>);

    expect(await screen.findByText("Total Forecast: 105 Cups")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /^Product demand projection/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Forecast & Material Requirements" })).toBeInTheDocument();
    expect(screen.getByText("4.4 kg")).toBeInTheDocument();
  });
  it("moves Today to the left or right as the selected chart range changes", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><DemandForecastPage /></QueryClientProvider>);
    const range = await screen.findByRole("combobox", { name: "Chart range" });
    expect(range).toHaveValue("future");
    expect(screen.getByText("Today", { selector: "text" })).toHaveAttribute("x", "86");
    expect(screen.queryByText("H-3", { selector: "text" })).not.toBeInTheDocument();
    await user.selectOptions(range, "past");
    expect(screen.getByText("Today", { selector: "text" })).toHaveAttribute("x", "1074");
    expect(screen.queryByText("H+1", { selector: "text" })).not.toBeInTheDocument();
    await user.selectOptions(range, "both");
    expect(screen.getByText("H-3", { selector: "text" })).toBeInTheDocument();
    expect(screen.getByText("H+3", { selector: "text" })).toBeInTheDocument();
    expect(screen.getByText("Today", { selector: "text" })).toHaveAttribute("x", "580");
  });
});
