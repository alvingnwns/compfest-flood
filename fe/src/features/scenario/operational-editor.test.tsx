import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { BusinessImportResponse } from "@/domain/business-data";
import { scenarioFixture } from "@/mocks/data";
import { OperationalEditor } from "./operational-editor";
import { OPERATIONAL_PRESETS } from "./scenario-presets";

const sampleCustomBusinessData: BusinessImportResponse = {
  valid: true,
  businessSnapshotId: "business-test-123",
  businessDataSource: "custom",
  expiresAt: "2026-08-18T16:00:00.000Z",
  summary: {
    productsLoaded: 2,
    ordersLoaded: 2,
    inventoryRows: 2,
    materialsLoaded: 2,
    bomRelationships: 3,
    totalOrderValue: 9_280_000,
    currency: "IDR",
  },
  products: [
    { id: "P001", name: "Ayam Beku", unit: "unit" },
    { id: "P002", name: "Ikan Fillet", unit: "unit" },
  ],
  inventory: [
    { facilityId: "wh-west", productId: "P001", quantity: 150, unit: "unit" },
    { facilityId: "wh-east", productId: "P002", quantity: 220, unit: "unit" },
  ],
  errors: [],
};

describe("OperationalEditor", () => {
  it("renders pure template by default", () => {
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={OPERATIONAL_PRESETS[0].overrides}
        presetId="normal"
        custom={false}
        onChange={onChange}
      />
    );

    expect(screen.getByText("PERSEDIAAN GUDANG")).toBeInTheDocument();
    expect(screen.getByText("LIST KENDARAAN")).toBeInTheDocument();
    expect(screen.getByText("Gudang 1")).toBeInTheDocument();
    expect(screen.getByText("Gudang 2")).toBeInTheDocument();
  });

  it("auto-populates custom product names, warehouse inventories from uploaded business data with only active warehouses", () => {
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={{ vehicleOverrides: [], inventoryOverrides: [] }}
        presetId="normal"
        custom={false}
        businessData={sampleCustomBusinessData}
        onChange={onChange}
      />
    );

    expect(screen.getAllByText("Ayam Beku").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ikan Fillet").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Persediaan Ayam Beku di Gudang Barat")).toHaveValue(150);
    expect(screen.getByLabelText("Persediaan Ikan Fillet di Gudang Timur")).toHaveValue(220);

    // Verify it only renders the 2 warehouses from business data, not padded with Gudang 3 and Gudang 4
    expect(screen.queryByText("Gudang 3")).not.toBeInTheDocument();
    expect(screen.queryByText("Gudang 4")).not.toBeInTheDocument();
  });

  it("restores demo warehouses and default quantities when businessData is cleared", () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={{ vehicleOverrides: [], inventoryOverrides: [] }}
        presetId="normal"
        custom={false}
        businessData={sampleCustomBusinessData}
        onChange={onChange}
      />
    );

    expect(screen.queryByText("Gudang 3")).not.toBeInTheDocument();

    // Rerender as demo data (businessData cleared to undefined)
    rerender(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={{ vehicleOverrides: [], inventoryOverrides: [] }}
        presetId="normal"
        custom={false}
        businessData={undefined}
        onChange={onChange}
      />
    );

    expect(screen.getByText("Gudang 1")).toBeInTheDocument();
    expect(screen.getByText("Gudang 2")).toBeInTheDocument();
    expect(screen.getByText("Gudang 3")).toBeInTheDocument();
    expect(screen.getByText("Gudang 4")).toBeInTheDocument();
  });

  it("allows inline editing of product name in a warehouse", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={{ vehicleOverrides: [], inventoryOverrides: [] }}
        presetId="normal"
        custom={false}
        onChange={onChange}
      />
    );

    const editProdBtn = screen.getByRole("button", { name: "Ubah nama Produk 1 di Gudang 1" });
    await user.click(editProdBtn);

    const input = screen.getByDisplayValue("Produk 1");
    await user.clear(input);
    await user.type(input, "Daging Sapi Premium{Enter}");

    expect(screen.getByText("Daging Sapi Premium")).toBeInTheDocument();
    expect(onChange).toHaveBeenCalled();
  });

  it("allows inline editing of warehouse name", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={{ vehicleOverrides: [], inventoryOverrides: [] }}
        presetId="normal"
        custom={false}
        onChange={onChange}
      />
    );

    const editWhBtn = screen.getByRole("button", { name: "Ubah nama Gudang 1" });
    await user.click(editWhBtn);

    const input = screen.getByDisplayValue("Gudang 1");
    await user.clear(input);
    await user.type(input, "Gudang Sentral Cikarang{Enter}");

    expect(screen.getByText("Gudang Sentral Cikarang")).toBeInTheDocument();
    expect(onChange).toHaveBeenCalled();
  });
});
