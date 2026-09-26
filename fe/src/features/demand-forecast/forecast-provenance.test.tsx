import { vi, it, expect, afterEach } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "api", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DemandForecastPage } from "./demand-forecast-page";
afterEach(() => vi.unstubAllGlobals());
it.each([ ["FALLBACK", "SYNTHETIC_DEMAND", "Synthetic history"], ["XGBOOST", "OBSERVED_SALES", "Observed sales"] ])("shows %s provenance independently from synthetic training", async (source, historySource, label) => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => Response.json(url.endsWith("/products")
    ? { products: [{ id: "P009", name: "Strawberry Juice", price: 20000, currency: "IDR", isActive: true }] }
    : { product: { id: "P009", name: "Strawberry Juice" }, generatedAt: "2026-09-26T08:00:00Z", horizonDays: 3, model: { name: source === "FALLBACK" ? "training-profile-mean" : "xgboost", version: "v1" }, source, trainingDataSynthetic: true, isSynthetic: source === "FALLBACK", fallbackReason: source === "FALLBACK" ? "INSUFFICIENT_OBSERVED_SALES_HISTORY" : null, history: [{ date: "2026-09-25", actualDemand: 10, historySource }], forecast: [1, 2, 3].map((horizon) => ({ date: `2026-09-${25 + horizon}`, horizon, predictedDemand: 15 })), ingredientRequirements: [] })));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DemandForecastPage /></QueryClientProvider>);
  const user = userEvent.setup();
  const info = await screen.findByText(source === "FALLBACK" ? "Estimated forecast · About this data" : "Model forecast · About this data");
  await user.click(info);
  expect(screen.getByText("Synthetic training data: Yes")).toBeVisible();
  await user.selectOptions(screen.getByRole("combobox", { name: "Chart range" }), "both");
  expect(screen.getByText(label)).toBeInTheDocument();
  expect(screen.queryByText("Actual")).not.toBeInTheDocument();
  expect(screen.queryByText(/INSUFFICIENT_OBSERVED_SALES_HISTORY/)).not.toBeInTheDocument();
  expect(screen.queryByText(/training-profile-mean/)).not.toBeInTheDocument();
  expect(screen.queryByText("Total ingredient requirements (3 days)")).not.toBeInTheDocument();
  if (source === "FALLBACK") expect(screen.getByText(/not live XGBoost output/)).toBeVisible();
  else expect(screen.queryByText(/not live XGBoost output/)).not.toBeInTheDocument();
});
