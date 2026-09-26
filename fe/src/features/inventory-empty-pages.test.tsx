import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InventoryLanguageProvider } from "@/components/providers/inventory-language-provider";
import { DashboardPage } from "./dashboard/dashboard-page";
import { SalesPage } from "./sales/sales-page";
import { InventoryPage } from "./inventory/inventory-page";
import { DemandForecastPage } from "./demand-forecast/demand-forecast-page";
import { StockRiskPage } from "./stock-risk/stock-risk-page";
import { OptimizationPlanPage } from "./optimization-plan/optimization-plan-page";
import { PosSimulatorPage } from "./pos-simulator/pos-simulator-page";
import { dashboardSummaryMock } from "@/mocks/dashboard-data";
import { inventoryOverviewMock } from "@/mocks/inventory-data";
import { optimizationPlanMock } from "@/mocks/optimization-plan-data";
import { posCatalogueMock } from "@/mocks/pos-simulator-data";
import { stockRiskOverviewMock } from "@/mocks/stock-risk-data";
import { demandForecastMock } from "@/mocks/demand-forecast-data";
import { salesOverviewMock } from "@/mocks/sales-data";

const loaders = vi.hoisted(() => ({
  overview: vi.fn(), sales: vi.fn(), inventory: vi.fn(), forecast: vi.fn(),
  risk: vi.fn(), optimization: vi.fn(), pos: vi.fn(),
}));
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "mock", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
vi.mock("@/services/dashboard-service", () => ({ dashboardService: { getSummary: loaders.overview } }));
vi.mock("@/services/sales-service", () => ({ salesService: { getOverview: loaders.sales, getTransaction: vi.fn() } }));
vi.mock("@/services/inventory-service", () => ({ inventoryService: { getOverview: loaders.inventory } }));
vi.mock("@/services/demand-forecast-service", () => ({ demandForecastService: { getForecast: loaders.forecast } }));
vi.mock("@/services/stock-risk-service", () => ({ stockRiskService: { getOverview: loaders.risk } }));
vi.mock("@/services/optimization-plan-service", () => ({ optimizationPlanService: { getPlan: loaders.optimization } }));
vi.mock("@/services/pos-simulator-service", () => ({ posSimulatorService: { getCatalogue: loaders.pos } }));

function mount(Page: React.ComponentType) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(<QueryClientProvider client={client}><InventoryLanguageProvider><Page /></InventoryLanguageProvider></QueryClientProvider>);
}
const cases = [
  ["overview", DashboardPage, "No data yet"],
  ["sales", SalesPage, "No sales today"],
  ["inventory", InventoryPage, "No stock movements yet"],
  ["forecast", DemandForecastPage, "No forecast available yet"],
  ["risk", StockRiskPage, "No stock data to analyze"],
  ["optimization", OptimizationPlanPage, "No optimization recommendations"],
  ["pos", PosSimulatorPage, "No products available"],
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  loaders.overview.mockResolvedValue({ ...dashboardSummaryMock, hasInventoryData: false, metrics: dashboardSummaryMock.metrics.map((metric) => ({ ...metric, value: 0 })), inventoryRisks: [], demandProjection: [], priorityRecommendations: [] });
  loaders.sales.mockResolvedValue({ ...salesOverviewMock, transactions: [], summary: { revenue: 0, transactionCount: 0, cupsSold: 0 } });
  loaders.inventory.mockResolvedValue({ ...inventoryOverviewMock, materials: [], movements: [] });
  loaders.forecast.mockResolvedValue({ ...demandForecastMock, productId: "", productName: "", products: [], points: [], details: [], totalPredictedSales: 0 });
  loaders.risk.mockResolvedValue({ ...stockRiskOverviewMock, materials: [] });
  loaders.optimization.mockResolvedValue({ ...optimizationPlanMock, actions: [] });
  loaders.pos.mockResolvedValue({ ...posCatalogueMock, products: [], initialOrder: [] });
});

describe("Inventory page states", () => {
  it.each(cases)("renders a successful empty %s without an unsupported import action", async (_key, Page, title) => {
    mount(Page);
    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /import/i })).not.toBeInTheDocument();
  });
  it.each(cases)("keeps a failed %s query distinct from empty data", async (key, Page, title) => {
    loaders[key].mockRejectedValue(new Error("API unavailable"));
    mount(Page);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load data");
    expect(screen.queryByRole("heading", { name: title })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
  });
  it.each(cases)("shows loading before the %s query resolves", (_key, Page, title) => {
    loaders[_key].mockImplementation(() => new Promise(() => undefined));
    mount(Page);
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByRole("heading", { name: title })).not.toBeInTheDocument();
  });
  it("switches empty inventory tabs and translates the empty state", async () => {
    const user = userEvent.setup();
    mount(InventoryPage);
    await screen.findByRole("heading", { name: "No stock movements yet" });
    await user.click(screen.getByRole("button", { name: "View Material Stock" }));
    expect(screen.getByRole("heading", { name: "No inventory data" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Switch to Bahasa Indonesia" }));
    expect(screen.getByRole("heading", { name: "Belum Ada Data Inventaris" })).toBeInTheDocument();
  });
  it("does not treat valid zero forecasts as missing data", async () => {
    loaders.forecast.mockResolvedValue({ ...demandForecastMock, totalPredictedSales: 0, details: demandForecastMock.details.map((row) => ({ ...row, predictedSales: 0 })) });
    mount(DemandForecastPage);
    expect(await screen.findByRole("heading", { name: "Forecast & Material Requirements" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No forecast available yet" })).not.toBeInTheDocument();
  });
  it("keeps inventory data visible when there are no daily sales", async () => {
    loaders.overview.mockResolvedValue({ ...dashboardSummaryMock, hasInventoryData: true, metrics: dashboardSummaryMock.metrics.map((metric) => ({ ...metric, value: 0 })), inventoryRisks: [], demandProjection: [], priorityRecommendations: [] });
    mount(DashboardPage);
    expect(await screen.findByText("Gross Sales")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No data yet" })).not.toBeInTheDocument();
  });
  it("keeps safe stock visible rather than showing no risk data", async () => {
    loaders.risk.mockResolvedValue({ ...stockRiskOverviewMock, materials: stockRiskOverviewMock.materials.map((row) => ({ ...row, status: "normal" })) });
    mount(StockRiskPage);
    expect(await screen.findByText("Raw Material Risk Analysis")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No stock data to analyze" })).not.toBeInTheDocument();
  });
  it("keeps inventory table headers when search finds no matching materials", async () => {
    const user = userEvent.setup();
    loaders.inventory.mockResolvedValue(inventoryOverviewMock);
    mount(InventoryPage);
    await screen.findByPlaceholderText("Enter material name...");
    await user.type(screen.getByPlaceholderText("Enter material name..."), "nonexistent-material");
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No stock movements yet" })).not.toBeInTheDocument();
  });
  it("keeps an empty basket usable when the product catalogue is populated", async () => {
    loaders.pos.mockResolvedValue({ ...posCatalogueMock, initialOrder: [] });
    mount(PosSimulatorPage);
    expect(await screen.findByRole("heading", { name: "Current Order" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "No products available" })).not.toBeInTheDocument();
  });
  it("explains an infeasible plan without displaying raw solver diagnostics", async () => {
    loaders.optimization.mockResolvedValue({ ...optimizationPlanMock, actions: [], optimizerStatus: "INFEASIBLE", outcome: "NO_PLAN", limitations: ["No feasible supplier offer."] });
    mount(OptimizationPlanPage);
    await screen.findByRole("heading", { name: "No optimization recommendations" });
    expect(screen.getByRole("status")).toHaveTextContent("No feasible purchasing plan is available.");
    expect(screen.queryByText(/INFEASIBLE/)).not.toBeInTheDocument();
    expect(screen.queryByText("No feasible supplier offer.")).not.toBeInTheDocument();
  });
  it("retries a failed query and then shows a successful empty response", async () => {
    const user = userEvent.setup();
    loaders.pos.mockRejectedValueOnce(new Error("API unavailable"));
    mount(PosSimulatorPage);
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "Try Again" }));
    expect(await screen.findByRole("heading", { name: "No products available" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("omits the technical forecast footer from the overview", async () => {
    loaders.overview.mockResolvedValue({ ...dashboardSummaryMock, source: "api", forecastSources: ["FALLBACK"], historySources: ["SYNTHETIC_DEMAND"], trainingDataSynthetic: true });
    mount(DashboardPage);
    await screen.findByText("Gross Sales");
    expect(screen.queryByText(/Forecast sources:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/History sources:/)).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Pending actions table" })).toHaveAttribute("tabindex", "0");
  });
  it("omits raw risk prose from material details", async () => {
    const user = userEvent.setup();
    loaders.inventory.mockResolvedValue({ ...inventoryOverviewMock, materials: inventoryOverviewMock.materials.map((material) => ({ ...material, riskReason: "Stok diproyeksikan menjadi negatif dalam horizon tiga hari." })) });
    mount(InventoryPage);
    await screen.findByPlaceholderText("Enter material name...");
    await user.click(screen.getByRole("tab", { name: "Material Stock" }));
    expect(screen.getByText("Remaining Stock")).toBeInTheDocument();
    expect(screen.queryByText("Stok diproyeksikan menjadi negatif dalam horizon tiga hari.")).not.toBeInTheDocument();
  });
  it("omits raw solver status and diagnostic codes from the plan", async () => {
    loaders.optimization.mockResolvedValue({ ...optimizationPlanMock, optimizerStatus: "OPTIMAL", outcome: "COMPLETE", totalCost: 900000, limitations: ["APPROVED_QUANTITY_UNCONFIRMED:ing_alpukat:25000000"] });
    mount(OptimizationPlanPage);
    await screen.findByRole("heading", { name: "System Optimization Recommendations" });
    expect(screen.queryByText(/Solver:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/APPROVED_QUANTITY_UNCONFIRMED/)).not.toBeInTheDocument();
  });
});
