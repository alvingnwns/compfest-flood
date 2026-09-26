import { afterEach, describe, expect, it, vi } from "vitest";
vi.mock("@/config/public-env", () => ({ publicEnv: { NEXT_PUBLIC_DATA_SOURCE: "api", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000" } }));
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SalesHistoryImport } from "./sales-history-import";

const coverage = { asOfDate: "2026-09-25", coveredDays: 0, requiredDays: 29, ready: false, missingDates: [], importedDays: 0, importedFirstDate: null, importedLastDate: null };
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const csv = () => new File(["date,product_id,quantity\n2026-08-01,P001,12\n"], "history.csv", { type: "text/csv" });
afterEach(() => vi.unstubAllGlobals());

function renderImport() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><SalesHistoryImport locale="en" onClose={() => undefined} /></QueryClientProvider>);
}

describe("SalesHistoryImport", () => {
  it("shows model coverage and uploads the CSV as multipart with an idempotency key", async () => {
    const user = userEvent.setup();
    const fetch = vi.fn()
      .mockResolvedValueOnce(reply(coverage))
      .mockResolvedValueOnce(reply({ batchId: "batch-1", importedAt: "2026-09-26T08:00:00Z", rowsReceived: 58, daysImported: 29, productsImported: 2, replacedDays: 0, firstDate: "2026-08-28", lastDate: "2026-09-25", coverage: { ...coverage, coveredDays: 29, ready: true } }, 201))
      .mockResolvedValue(reply({ ...coverage, coveredDays: 29, ready: true }));
    vi.stubGlobal("fetch", fetch);
    renderImport();

    expect(await screen.findByText("0/29")).toBeInTheDocument();
    expect(screen.getByText(/29 more days needed/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Download template/ })).toHaveAttribute("href", "http://localhost:8000/api/sales-history/template");
    const upload = screen.getByRole("button", { name: "Upload" });
    expect(upload).toBeDisabled();
    await user.upload(screen.getByLabelText("Sales history CSV file"), csv());
    await user.click(upload);

    expect(await screen.findByRole("status")).toHaveTextContent("Imported 29 days (2026-08-28 to 2026-09-25) for 2 products.");
    const [url, init] = fetch.mock.calls[1];
    expect(url).toBe("http://localhost:8000/api/sales-history/imports");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(init.headers["Content-Type"]).toBeUndefined();
    expect(init.headers["Idempotency-Key"]).toMatch(/[0-9a-f-]{36}/);
  });

  it("explains rejected files with line-numbered errors", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(reply(coverage))
      .mockResolvedValueOnce(reply({ error: { code: "INVALID_SALES_HISTORY_ROWS", message: "Ada baris yang tidak valid.", details: { errors: [{ line: 3, error: "produk tidak dikenal: P999" }] } } }, 422)));
    renderImport();

    await user.upload(screen.getByLabelText("Sales history CSV file"), csv());
    await user.click(screen.getByRole("button", { name: "Upload" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Some rows are invalid. Nothing was imported");
    expect(alert).toHaveTextContent("Line 3: produk tidak dikenal: P999");
  });
});
