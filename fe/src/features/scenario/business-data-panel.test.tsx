import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BusinessImportResponse } from "@/domain/business-data";
import { ApiError } from "@/lib/api-client";
import { BusinessDataPanel } from "./business-data-panel";

const preview: BusinessImportResponse = {
  valid: true,
  businessSnapshotId: "business-test",
  businessDataSource: "custom",
  expiresAt: "2026-08-18T16:00:00.000Z",
  summary: {
    productsLoaded: 2,
    ordersLoaded: 20,
    inventoryRows: 4,
    materialsLoaded: 3,
    bomRelationships: 5,
    totalOrderValue: 2_000_000,
    currency: "IDR",
  },
  errors: [],
};

describe("BusinessDataPanel", () => {
  it("shows demo mode by default and exposes custom template workflow", async () => {
    const user = userEvent.setup();
    const onModeChange = vi.fn();
    const { rerender } = render(
      <BusinessDataPanel mode="demo" pending={false} onModeChange={onModeChange} onUpload={vi.fn()} onConfirm={vi.fn()} />,
    );
    expect(screen.getByRole("radio", { name: /Demo Business Data/ })).toBeChecked();
    await user.click(screen.getByRole("radio", { name: /Custom Business Data/ }));
    expect(onModeChange).toHaveBeenCalledWith("custom");

    rerender(<BusinessDataPanel mode="custom" pending={false} onModeChange={onModeChange} onUpload={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("link", { name: /Download Excel Template/ })).toHaveAttribute("href", expect.stringContaining("/api/business-data/template"));
    expect(screen.getByText(/jaringan logistik demo Jakarta/i)).toBeInTheDocument();
  });

  it("rejects non-xlsx files before upload", async () => {
    const user = userEvent.setup({ applyAccept: false });
    const onUpload = vi.fn();
    render(<BusinessDataPanel mode="custom" pending={false} onModeChange={vi.fn()} onUpload={onUpload} onConfirm={vi.fn()} />);
    await user.upload(screen.getByLabelText("Upload Business Data"), new File(["bad"], "data.csv", { type: "text/csv" }));
    expect(onUpload).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/format .xlsx/i);
  });

  it("renders preview and activates only after confirmation", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const { rerender } = render(
      <BusinessDataPanel mode="custom" preview={preview} pending={false} onModeChange={vi.fn()} onUpload={vi.fn()} onConfirm={onConfirm} />,
    );
    expect(screen.getByText("Data tervalidasi")).toBeInTheDocument();
    expect(screen.getByText("Rp 2.000.000")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Gunakan Data" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    rerender(<BusinessDataPanel mode="custom" preview={preview} activeSnapshotId="business-test" pending={false} onModeChange={vi.fn()} onUpload={vi.fn()} onConfirm={onConfirm} />);
    expect(screen.getByText("Business Data: Custom Upload")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Data Aktif" })).toBeDisabled();
  });

  it("shows structured workbook validation details", () => {
    const error = new ApiError(422, {
      code: "BUSINESS_DATA_VALIDATION_FAILED",
      message: "invalid",
      retryable: false,
      details: {
        errors: [{ sheet: "Orders", row: 7, column: "productId", code: "UNKNOWN_PRODUCT", message: "Orders row 7 references unknown productId 'P003'." }],
      },
    });
    render(<BusinessDataPanel mode="custom" pending={false} error={error} onModeChange={vi.fn()} onUpload={vi.fn()} onConfirm={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Orders row 7 references unknown productId 'P003'.");
  });
});
