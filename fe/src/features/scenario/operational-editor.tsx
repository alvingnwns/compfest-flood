"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { BusinessImportResponse } from "@/domain/business-data";
import type { CustomVehicle, Scenario, VehicleOverride } from "@/domain/scenario";
import type { OperationalOverrides } from "./scenario-presets";

type Props = {
  scenario: Scenario;
  overrides: OperationalOverrides;
  presetId?: string;
  custom?: boolean;
  businessData?: BusinessImportResponse;
  disabled?: boolean;
  onChange: (overrides: OperationalOverrides) => void;
};

type ProductItem = {
  id: string;
  name: string;
  quantity: number;
};

type WarehouseItem = {
  id: string;
  name: string;
  items: ProductItem[];
};

type VehicleItem = {
  id: string;
  label: string;
  capacityUnits: number;
  available: boolean;
  custom: boolean;
};

const warehouseHeaderColors = ["bg-[#5c2a72]", "bg-[#2e7d32]"];

function createWarehouseItems(
  scenario: Scenario,
  overrides: OperationalOverrides,
  businessData?: BusinessImportResponse
): WarehouseItem[] {
  const warehouses = scenario.facilities.filter((facility) => facility.kind === "warehouse");
  const products =
    businessData?.products && businessData.products.length > 0
      ? businessData.products
      : scenario.products;
  const inventory =
    businessData?.inventory && businessData.inventory.length > 0
      ? businessData.inventory
      : scenario.inventory;
  const overrideIndex = new Map(
    overrides.inventoryOverrides.map((item) => [
      `${item.facilityId}:${item.productId}`,
      item.quantity,
    ])
  );

  return warehouses.map((warehouse) => ({
    id: warehouse.id,
    name: warehouse.name,
    items: products.map((product) => ({
      id: product.id,
      name: product.name,
      quantity:
        overrideIndex.get(`${warehouse.id}:${product.id}`) ??
        inventory.find(
          (item) => item.facilityId === warehouse.id && item.productId === product.id
        )?.quantity ??
        0,
    })),
  }));
}

function createVehicleItems(
  scenario: Scenario,
  overrides: OperationalOverrides
): VehicleItem[] {
  const overrideIndex = new Map(overrides.vehicleOverrides.map((item) => [item.id, item]));
  const existing = scenario.vehicles.map((vehicle) => {
    const override = overrideIndex.get(vehicle.id);
    return {
      id: vehicle.id,
      label: vehicle.label,
      capacityUnits: override?.capacityUnits ?? vehicle.capacityUnits,
      available: override?.available ?? vehicle.available,
      custom: false,
    };
  });
  const custom = (overrides.customVehicles ?? []).map((vehicle) => ({
    ...vehicle,
    custom: true,
  }));
  return [...existing, ...custom];
}

function OperationalEditorState({
  scenario,
  overrides,
  businessData,
  disabled,
  onChange,
}: Props) {
  const [warehouses, setWarehouses] = useState<WarehouseItem[]>(() =>
    createWarehouseItems(scenario, overrides, businessData)
  );
  const [vehicles, setVehicles] = useState<VehicleItem[]>(() =>
    createVehicleItems(scenario, overrides)
  );

  const emitChange = (
    updatedVehicles: VehicleItem[],
    updatedWarehouses: WarehouseItem[]
  ) => {
    const vehicleOverrides: VehicleOverride[] = updatedVehicles
      .filter((vehicle) => !vehicle.custom)
      .map((vehicle) => ({
        id: vehicle.id,
        available: vehicle.available,
        capacityUnits: vehicle.capacityUnits,
      }));
    const customVehicles: CustomVehicle[] = updatedVehicles
      .filter((vehicle) => vehicle.custom)
      .map(({ id, label, capacityUnits, available }) => ({
        id,
        label,
        capacityUnits,
        available,
      }));
    const inventoryOverrides = updatedWarehouses.flatMap((warehouse) =>
      warehouse.items.map((item) => ({
        facilityId: warehouse.id,
        productId: item.id,
        quantity: item.quantity,
      }))
    );

    onChange({ vehicleOverrides, customVehicles, inventoryOverrides });
  };

  const updateInventory = (
    facilityId: string,
    productId: string,
    quantity: number
  ) => {
    const validQuantity = Math.max(0, Number.isNaN(quantity) ? 0 : quantity);
    const next = warehouses.map((warehouse) =>
      warehouse.id === facilityId
        ? {
            ...warehouse,
            items: warehouse.items.map((item) =>
              item.id === productId ? { ...item, quantity: validQuantity } : item
            ),
          }
        : warehouse
    );
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  const addVehicle = () => {
    if (disabled) return;
    const usedIds = new Set(vehicles.map((vehicle) => vehicle.id));
    let nextNumber = 1;
    while (usedIds.has(`V-${String(nextNumber).padStart(2, "0")}`)) {
      nextNumber += 1;
    }
    const newVehicle: VehicleItem = {
      id: `V-${String(nextNumber).padStart(2, "0")}`,
      label: `Kendaraan ${String(nextNumber).padStart(2, "0")}`,
      capacityUnits: 500,
      available: true,
      custom: true,
    };
    const next = [...vehicles, newVehicle];
    setVehicles(next);
    emitChange(next, warehouses);
  };

  const updateVehicle = (id: string, update: Partial<VehicleItem>) => {
    const next = vehicles.map((vehicle) =>
      vehicle.id === id ? { ...vehicle, ...update } : vehicle
    );
    setVehicles(next);
    emitChange(next, warehouses);
  };

  const removeVehicle = (id: string) => {
    const next = vehicles.filter((vehicle) => !(vehicle.id === id && vehicle.custom));
    setVehicles(next);
    emitChange(next, warehouses);
  };

  return (
    <div className="mx-auto w-full max-w-[1456px]">
      <p className="mb-5 text-center text-[13px] leading-relaxed text-primary/75 md:text-[14px]">
        Jaringan gudang menggunakan fasilitas yang telah ditentukan untuk simulasi MVP.
        Stok setiap gudang tetap dapat disesuaikan. Kendaraan tambahan yang Anda
        konfigurasi akan disertakan dalam simulasi.
      </p>
      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] xl:gap-8">
        <section aria-labelledby="warehouse-title">
          <div className="mb-4 flex items-center justify-between">
            <h2
              id="warehouse-title"
              className="text-[20px] font-bold text-primary-dark md:text-[22px]"
            >
              PERSEDIAAN GUDANG
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {warehouses.map((warehouse, warehouseIndex) => (
              <article
                key={warehouse.id}
                className="overflow-hidden rounded-[22px] border border-outline/40 bg-white shadow-sm"
              >
                <header
                  className={`flex h-[48px] items-center px-4 text-white ${
                    warehouseHeaderColors[warehouseIndex % warehouseHeaderColors.length]
                  }`}
                >
                  <h3 className="text-[16px] font-bold md:text-[17px]">
                    {warehouse.name}
                  </h3>
                </header>
                <div className="space-y-2 p-3.5">
                  {warehouse.items.map((item) => (
                    <div
                      key={item.id}
                      className="grid grid-cols-[minmax(0,1fr)_72px] items-center gap-2"
                    >
                      <span
                        className="truncate text-[13px] font-bold text-primary-dark"
                        title={item.name}
                      >
                        {item.name}
                      </span>
                      <input
                        type="number"
                        min={0}
                        disabled={disabled}
                        value={item.quantity}
                        aria-label={`Persediaan ${item.name} di ${warehouse.name}`}
                        onChange={(event) =>
                          updateInventory(
                            warehouse.id,
                            item.id,
                            Number(event.target.value)
                          )
                        }
                        className="h-8 w-full rounded-[8px] border border-outline bg-[#fafafa] px-2 text-right text-[14px] font-bold text-primary-dark focus:border-primary"
                      />
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="vehicle-title">
          <div className="mb-4 flex items-center justify-between">
            <h2
              id="vehicle-title"
              className="text-[20px] font-bold text-primary-dark md:text-[22px]"
            >
              LIST KENDARAAN
            </h2>
            <button
              type="button"
              disabled={disabled}
              onClick={addVehicle}
              aria-label="Tambah kendaraan"
              title="Tambah kendaraan baru"
              className="grid h-9 w-9 place-items-center rounded-full bg-primary-dark text-white shadow-sm transition hover:brightness-110 active:scale-95 disabled:opacity-50"
            >
              <Plus className="h-5 w-5 text-white" aria-hidden="true" />
            </button>
          </div>
          <div className="space-y-3">
            {vehicles.map((vehicle) => (
              <article
                key={vehicle.id}
                className="rounded-[22px] bg-[#345173] p-4 text-white shadow-sm md:p-5"
              >
                <div className="mb-2.5 flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="text-[11px] font-bold uppercase tracking-wide text-white/65">
                        {vehicle.custom ? "Ditambahkan" : "Armada utama"}
                      </span>
                      <span className="rounded-full bg-white/15 px-2 py-0.5 text-[11px] font-bold">
                        {vehicle.id}
                      </span>
                    </div>
                    {vehicle.custom ? (
                      <input
                        type="text"
                        disabled={disabled}
                        value={vehicle.label}
                        aria-label={`Nama kendaraan ${vehicle.id}`}
                        onChange={(event) =>
                          updateVehicle(vehicle.id, { label: event.target.value })
                        }
                        className="h-8 w-full max-w-56 rounded-lg border border-white/20 bg-white/10 px-2 text-[15px] font-bold text-white focus:border-white/60 focus:outline-none disabled:opacity-55"
                      />
                    ) : (
                      <h3 className="truncate text-[15px] font-bold md:text-[16px]">
                        {vehicle.label}
                      </h3>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      role="switch"
                      aria-checked={vehicle.available}
                      aria-label={`Status kendaraan ${vehicle.id}`}
                      disabled={disabled}
                      onClick={() =>
                        updateVehicle(vehicle.id, { available: !vehicle.available })
                      }
                      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                        vehicle.available ? "bg-[#eba92d]" : "bg-white/30"
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block size-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          vehicle.available ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                    <span className="text-[13px] font-bold">
                      {vehicle.available ? "Aktif" : "Non-Aktif"}
                    </span>
                    {vehicle.custom ? (
                      <button
                        type="button"
                        disabled={disabled}
                        onClick={() => removeVehicle(vehicle.id)}
                        aria-label={`Hapus kendaraan ${vehicle.id}`}
                        title="Hapus kendaraan tambahan"
                        className="grid size-8 place-items-center rounded-full bg-white/10 transition hover:bg-red-500/80 disabled:opacity-50"
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="flex items-center gap-2.5">
                  <label
                    htmlFor={`cap-${vehicle.id}`}
                    className="shrink-0 text-[13px] font-semibold text-white/90 md:text-[14px]"
                  >
                    Kapasitas:
                  </label>
                  <input
                    id={`cap-${vehicle.id}`}
                    type="number"
                    min={1}
                    max={1_000_000}
                    disabled={disabled}
                    value={vehicle.capacityUnits}
                    aria-label={`Kapasitas kendaraan ${vehicle.id}`}
                    onChange={(event) =>
                      updateVehicle(vehicle.id, {
                        capacityUnits: Math.min(
                          1_000_000,
                          Math.max(
                            1,
                            Number.isNaN(Number(event.target.value))
                              ? 1
                              : Number(event.target.value)
                          )
                        ),
                      })
                    }
                    className="h-9 min-w-0 flex-1 rounded-[10px] border-0 bg-white px-4 text-[13px] font-medium text-black disabled:opacity-55 md:text-[14px]"
                  />
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

export function OperationalEditor(props: Props) {
  const dataKey = props.businessData?.businessSnapshotId ?? "demo";
  return (
    <OperationalEditorState
      key={`${props.presetId ?? "normal"}:${dataKey}:${props.custom ?? false}`}
      {...props}
    />
  );
}
