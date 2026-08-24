import { fireEvent, render, screen } from "@testing-library/react";
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

const emptyOverrides = { vehicleOverrides: [], customVehicles: [], inventoryOverrides: [] };

describe("OperationalEditor", () => {
  it("shows only authoritative warehouses with read-only identities", () => {
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={OPERATIONAL_PRESETS[0].overrides}
        presetId="normal"
        custom={false}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByText("Gudang Timur")).toBeInTheDocument();
    expect(screen.getByText("Gudang Barat")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Tambah gudang/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ubah nama Gudang/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Gudang 3")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tambah kendaraan" })).toBeInTheDocument();
  });

  it("keeps inventory editing connected to inventory overrides", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={emptyOverrides}
        presetId="normal"
        custom={false}
        onChange={onChange}
      />
    );

    const inventory = screen.getByLabelText("Persediaan Produk A di Gudang Barat");
    await user.clear(inventory);
    await user.type(inventory, "275");

    const latest = onChange.mock.calls.at(-1)?.[0];
    expect(latest.inventoryOverrides).toContainEqual({
      facilityId: "wh-west",
      productId: "prod-a",
      quantity: 275,
    });
  });

  it("uses uploaded products while preserving predefined warehouse identities", () => {
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={emptyOverrides}
        presetId="normal"
        custom={false}
        businessData={sampleCustomBusinessData}
        onChange={vi.fn()}
      />
    );

    expect(screen.getAllByText("Ayam Beku").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Persediaan Ayam Beku di Gudang Barat")).toHaveValue(150);
    expect(screen.getByLabelText("Persediaan Ikan Fillet di Gudang Timur")).toHaveValue(220);
    expect(screen.getByText("Gudang Barat")).toBeInTheDocument();
    expect(screen.getByText("Gudang Timur")).toBeInTheDocument();
  });

  it("adds, edits, deactivates, and removes a real custom vehicle payload", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={emptyOverrides}
        presetId="normal"
        custom={false}
        onChange={onChange}
      />
    );

    await user.click(screen.getByRole("button", { name: "Tambah kendaraan" }));
    expect(screen.getByText("V-04")).toBeInTheDocument();
    expect(onChange.mock.calls.at(-1)?.[0].customVehicles).toContainEqual({
      id: "V-04",
      label: "Kendaraan 04",
      capacityUnits: 500,
      available: true,
    });

    const capacity = screen.getByLabelText("Kapasitas kendaraan V-04");
    fireEvent.change(capacity, { target: { value: "900" } });
    const name = screen.getByLabelText("Nama kendaraan V-04");
    await user.clear(name);
    await user.type(name, "Armada Darurat");
    await user.click(screen.getByRole("switch", { name: "Status kendaraan V-04" }));

    expect(onChange.mock.calls.at(-1)?.[0].customVehicles).toContainEqual({
      id: "V-04",
      label: "Armada Darurat",
      capacityUnits: 900,
      available: false,
    });

    await user.click(screen.getByRole("button", { name: "Hapus kendaraan V-04" }));
    expect(screen.queryByText("V-04")).not.toBeInTheDocument();
    expect(onChange.mock.calls.at(-1)?.[0].customVehicles).toEqual([]);
  });

  it("keeps predefined vehicle identity read-only and non-deletable", () => {
    render(
      <OperationalEditor
        scenario={scenarioFixture}
        overrides={emptyOverrides}
        presetId="normal"
        custom={false}
        onChange={vi.fn()}
      />
    );

    expect(screen.getByText("Truk Boks 01")).toBeInTheDocument();
    expect(screen.queryByLabelText("Nama kendaraan V-01")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Hapus kendaraan V-01" })).not.toBeInTheDocument();
  });
});
