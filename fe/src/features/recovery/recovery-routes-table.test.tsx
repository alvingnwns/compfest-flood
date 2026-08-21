import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { LogisticsAction } from "@/domain/recovery";
import { RoutesView } from "./recovery-page";

const recommendation = {
  what: "Gunakan penyesuaian logistik hasil recovery.",
  why: "Keputusan berasal dari hasil optimizer.",
  expectedImpact: "Menjaga kelangsungan pengiriman.",
};

const actions: LogisticsAction[] = [
  {
    ...recommendation,
    id: "log-same-warehouse",
    orderId: "ORD-001",
    originalWarehouseId: "wh-west",
    originalWarehouseName: "Gudang Barat",
    recoveryWarehouseId: "wh-west",
    recoveryWarehouseName: "Gudang Barat",
    vehicleId: "V-02",
    baselineRouteId: "route-normal-1",
    recoveryRouteId: "route-recovery-1",
    baselineEtaMinutes: 7,
    recoveryEtaMinutes: 8,
    baselineFloodExposure: "high",
    recoveryFloodExposure: "low",
    action: "reroute",
  },
  {
    ...recommendation,
    id: "log-reallocated",
    orderId: "ORD-003",
    originalWarehouseId: "wh-east",
    originalWarehouseName: "Gudang Timur",
    recoveryWarehouseId: "wh-west",
    recoveryWarehouseName: "Gudang Barat",
    vehicleId: "V-03",
    baselineRouteId: "route-normal-2",
    recoveryRouteId: "route-recovery-2",
    baselineEtaMinutes: 19,
    recoveryEtaMinutes: 27,
    baselineFloodExposure: "critical",
    recoveryFloodExposure: "medium",
    action: "reallocate-reroute",
  },
  {
    ...recommendation,
    id: "log-equal-eta",
    orderId: "ORD-002",
    originalWarehouseId: "wh-east",
    originalWarehouseName: "Gudang Timur",
    recoveryWarehouseId: "wh-east",
    recoveryWarehouseName: "Gudang Timur",
    vehicleId: "V-01",
    baselineRouteId: "route-normal-3",
    recoveryRouteId: "route-recovery-3",
    baselineEtaMinutes: 16,
    recoveryEtaMinutes: 16,
    baselineFloodExposure: "high",
    recoveryFloodExposure: "low",
    action: "reroute",
  },
  {
    ...recommendation,
    id: "log-new-allocation",
    orderId: "ORD-012",
    recoveryWarehouseId: "wh-west",
    recoveryWarehouseName: "Gudang Barat",
    vehicleId: "V-03",
    recoveryRouteId: "route-recovery-wh-west-store-b",
    recoveryEtaMinutes: 16,
    recoveryFloodExposure: "medium",
    action: "allocate",
  },
];

const destinations = [
  { orderId: "ORD-001", storeId: "store-a", storeName: "Toko A" },
  { orderId: "ORD-002", storeId: "store-b", storeName: "Toko B" },
  { orderId: "ORD-003", storeId: "store-c", storeName: "Toko C" },
  { orderId: "ORD-012", storeId: "store-b", storeName: "Toko B" },
];

describe("Recovery logistics table semantics", () => {
  it("separates baseline and recovery warehouses from their ETA values", () => {
    render(<RoutesView actions={actions} destinations={destinations} />);
    expect(
      screen.getByRole("columnheader", { name: "Pesanan / Tujuan" }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("columnheader", { name: "Gudang Normal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Gudang Pemulihan" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "ETA Normal" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "ETA Pemulihan" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "RUTE NORMAL" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("columnheader", { name: "RUTE PEMULIHAN" }),
    ).not.toBeInTheDocument();

    const firstRow = screen.getAllByRole("row")[1];
    expect(within(firstRow).getByText("Toko A")).toBeInTheDocument();
    expect(within(firstRow).getByText("ORD-001")).toBeInTheDocument();
    expect(within(firstRow).getAllByText("Gudang Barat")).toHaveLength(2);
    expect(within(firstRow).getByText("7m")).toBeInTheDocument();
    expect(within(firstRow).getByText("8m")).toBeInTheDocument();
    expect(within(firstRow).getByText("V-02")).toBeInTheDocument();
    expect(within(firstRow).getByText("Ubah rute")).toBeInTheDocument();
    expect(
      screen.queryByText("Gudang Barat - Gudang Barat"),
    ).not.toBeInTheDocument();
  });

  it("shows warehouse and route changes using the backend action value", () => {
    render(<RoutesView actions={actions} destinations={destinations} />);

    const secondRow = screen.getAllByRole("row")[2];
    expect(within(secondRow).getByText("Toko C")).toBeInTheDocument();
    expect(within(secondRow).getByText("ORD-003")).toBeInTheDocument();
    expect(within(secondRow).getByText("Gudang Timur")).toBeInTheDocument();
    expect(within(secondRow).getByText("Gudang Barat")).toBeInTheDocument();
    expect(within(secondRow).getByText("19m")).toBeInTheDocument();
    expect(within(secondRow).getByText("27m")).toBeInTheDocument();
    expect(within(secondRow).getByText("V-03")).toBeInTheDocument();
    expect(
      within(secondRow).getByText("Alihkan + ubah rute"),
    ).toBeInTheDocument();
  });

  it("preserves a route-change action when distinct route IDs have equal displayed ETA", () => {
    render(<RoutesView actions={actions} destinations={destinations} />);

    const thirdRow = screen.getAllByRole("row")[3];
    expect(within(thirdRow).getByText("Toko B")).toBeInTheDocument();
    expect(actions[2].baselineRouteId).not.toBe(actions[2].recoveryRouteId);
    expect(within(thirdRow).getAllByText("16m")).toHaveLength(2);
    expect(within(thirdRow).getByText("V-01")).toBeInTheDocument();
    expect(within(thirdRow).getByText("Ubah rute")).toBeInTheDocument();
  });

  it("shows a newly allocated order without inventing baseline warehouse or ETA", () => {
    render(<RoutesView actions={actions} destinations={destinations} />);

    const allocationRow = screen.getAllByRole("row")[4];
    expect(within(allocationRow).getByText("Toko B")).toBeInTheDocument();
    expect(within(allocationRow).getByText("ORD-012")).toBeInTheDocument();
    expect(
      within(allocationRow).getByText("Belum teralokasi"),
    ).toBeInTheDocument();
    expect(within(allocationRow).getByText("Gudang Barat")).toBeInTheDocument();
    expect(within(allocationRow).getByText("—")).toBeInTheDocument();
    expect(within(allocationRow).getByText("16m")).toBeInTheDocument();
    expect(within(allocationRow).getByText("V-03")).toBeInTheDocument();
    expect(
      within(allocationRow).getByText("Alokasikan pesanan"),
    ).toBeInTheDocument();
    expect(
      within(allocationRow).queryByText("Alihkan + ubah rute"),
    ).not.toBeInTheDocument();
  });
});
