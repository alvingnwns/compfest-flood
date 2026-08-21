"use client";

import { Check, Pencil, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import type { BusinessImportResponse } from "@/domain/business-data";
import type { Scenario, VehicleOverride } from "@/domain/scenario";
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
};

const warehouseHeaderColors = [
  "bg-[#5c2a72]",
  "bg-[#2e7d32]",
  "bg-[#880e4f]",
  "bg-[#af601a]",
];

function createPureTemplateWarehouses(presetId: string): WarehouseItem[] {
  const initialNames = ["Gudang 1", "Gudang 2", "Gudang 3", "Gudang 4"];
  const ids = ["wh-east", "wh-west", "wh-3", "wh-4"];

  return initialNames.map((name, index) => {
    let p1Qty = 0;
    let p2Qty = 0;
    if (presetId === "severe-disruption") {
      p1Qty = index === 0 ? 0 : index === 1 ? 310 : 0;
      p2Qty = index === 1 ? 500 : 0;
    } else if (presetId === "critical-stock") {
      p1Qty = index === 0 ? 50 : index === 1 ? 50 : 0;
      p2Qty = index === 1 ? 500 : 0;
    } else {
      // normal & limited-vehicle
      p1Qty = index === 0 ? 420 : index === 1 ? 310 : 0;
      p2Qty = index === 1 ? 500 : 0;
    }

    return {
      id: ids[index],
      name,
      items: [
        { id: "prod-1", name: "Produk 1", quantity: p1Qty },
        { id: "prod-2", name: "Produk 2", quantity: p2Qty },
        { id: "prod-3", name: "Produk 3", quantity: 0 },
      ],
    };
  });
}

function createWarehouseItems(
  scenario: Scenario,
  presetId: string,
  businessData?: BusinessImportResponse
): WarehouseItem[] {
  if (businessData && businessData.products && businessData.products.length > 0) {
    const invWarehouseIds = Array.from(
      new Set(businessData.inventory?.map((inv) => inv.facilityId).filter(Boolean) ?? [])
    );

    const warehouseIds =
      invWarehouseIds.length > 0
        ? invWarehouseIds
        : scenario.facilities.filter((f) => f.kind === "warehouse").map((w) => w.id);

    const finalWarehouseIds = warehouseIds.length > 0 ? warehouseIds : ["wh-east"];

    return finalWarehouseIds.map((whId, idx) => {
      const facility = scenario.facilities.find((f) => f.id === whId);
      const name = facility?.name ?? `Gudang ${idx + 1}`;

      const items: ProductItem[] = businessData.products.map((prod) => {
        const invRow = businessData.inventory?.find(
          (inv) => inv.facilityId === whId && inv.productId === prod.id
        );
        return {
          id: prod.id,
          name: prod.name,
          quantity: invRow ? invRow.quantity : 0,
        };
      });

      return {
        id: whId,
        name,
        items,
      };
    });
  }

  return createPureTemplateWarehouses(presetId);
}

function createPureTemplateVehicles(presetId: string): VehicleItem[] {
  return [
    {
      id: "V-01",
      label: "Kendaraan 1",
      capacityUnits: 800,
      available: presetId === "severe-disruption" ? false : true,
    },
    {
      id: "V-02",
      label: "Kendaraan 2",
      capacityUnits: 800,
      available: presetId === "severe-disruption" ? false : true,
    },
    {
      id: "V-03",
      label: "Kendaraan 3",
      capacityUnits: 450,
      available: presetId === "limited-vehicle" ? false : true,
    },
  ];
}

export function OperationalEditor({
  scenario,
  overrides,
  presetId = "severe-disruption",
  custom = false,
  businessData,
  disabled,
  onChange,
}: Props) {
  const [warehouses, setWarehouses] = useState<WarehouseItem[]>(() =>
    createWarehouseItems(scenario, presetId, businessData)
  );

  const [vehicles, setVehicles] = useState<VehicleItem[]>(() => createPureTemplateVehicles(presetId));

  // Inline editing state for warehouse, product, and vehicle
  const [editingWarehouseId, setEditingWarehouseId] = useState<string | null>(null);
  const [editingWarehouseName, setEditingWarehouseName] = useState("");
  const [editingProduct, setEditingProduct] = useState<{ warehouseId: string; productId: string } | null>(null);
  const [editingProductName, setEditingProductName] = useState("");
  const [editingVehicleId, setEditingVehicleId] = useState<string | null>(null);
  const [editingVehicleName, setEditingVehicleName] = useState("");

  const emitChange = (updatedVehicles: VehicleItem[], updatedWarehouses: WarehouseItem[]) => {
    const vehicleOverrides: VehicleOverride[] = updatedVehicles.map((v) => ({
      id: v.id,
      available: v.available,
      capacityUnits: v.capacityUnits,
    }));

    const inventoryOverrides = updatedWarehouses.flatMap((wh) =>
      wh.items.map((item) => ({
        facilityId: wh.id,
        productId: item.id,
        quantity: item.quantity,
      }))
    );

    onChange({ vehicleOverrides, inventoryOverrides });
  };

  useEffect(() => {
    if (!custom) {
      const newWarehouses = createWarehouseItems(scenario, presetId, businessData);
      const newVehicles = createPureTemplateVehicles(presetId);
      setWarehouses(newWarehouses);
      setVehicles(newVehicles);
    }
  }, [presetId, custom, businessData, scenario]);

  // Add Warehouse
  const addWarehouse = () => {
    if (disabled) return;
    const nextIndex = warehouses.length + 1;
    const sampleProducts = warehouses[0]?.items ?? [
      { id: "prod-1", name: "Produk 1", quantity: 0 },
      { id: "prod-2", name: "Produk 2", quantity: 0 },
      { id: "prod-3", name: "Produk 3", quantity: 0 },
    ];
    const newWarehouse: WarehouseItem = {
      id: `wh-${nextIndex}`,
      name: `Gudang ${nextIndex}`,
      items: sampleProducts.map((p) => ({ ...p, quantity: 0 })),
    };
    const next = [...warehouses, newWarehouse];
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  // Add Product to specific warehouse
  const addProductToWarehouse = (warehouseId: string) => {
    if (disabled) return;
    const next = warehouses.map((wh) => {
      if (wh.id !== warehouseId) return wh;
      const nextProdIndex = wh.items.length + 1;
      const newProduct: ProductItem = {
        id: `prod-${nextProdIndex}`,
        name: `Produk ${nextProdIndex}`,
        quantity: 0,
      };
      return { ...wh, items: [...wh.items, newProduct] };
    });
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  // Inline warehouse name edit
  const startEditWarehouse = (id: string, currentName: string) => {
    if (disabled) return;
    setEditingWarehouseId(id);
    setEditingWarehouseName(currentName);
  };

  const saveWarehouseName = (id: string) => {
    const trimmed = editingWarehouseName.trim();
    setEditingWarehouseId(null);
    if (!trimmed) return;
    const next = warehouses.map((wh) => (wh.id === id ? { ...wh, name: trimmed } : wh));
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  // Inline product name edit
  const startEditProduct = (warehouseId: string, productId: string, currentName: string) => {
    if (disabled) return;
    setEditingProduct({ warehouseId, productId });
    setEditingProductName(currentName);
  };

  const saveProductName = (warehouseId: string, productId: string) => {
    const trimmed = editingProductName.trim();
    setEditingProduct(null);
    if (!trimmed) return;
    const next = warehouses.map((wh) => {
      if (wh.id !== warehouseId) return wh;
      return {
        ...wh,
        items: wh.items.map((item) =>
          item.id === productId ? { ...item, name: trimmed } : item
        ),
      };
    });
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  // Update Inventory Quantity
  const updateInventory = (facilityId: string, productId: string, quantity: number) => {
    const validQty = Math.max(0, isNaN(quantity) ? 0 : quantity);
    const next = warehouses.map((wh) => {
      if (wh.id !== facilityId) return wh;
      return {
        ...wh,
        items: wh.items.map((item) => (item.id === productId ? { ...item, quantity: validQty } : item)),
      };
    });
    setWarehouses(next);
    emitChange(vehicles, next);
  };

  // Add Vehicle
  const addVehicle = () => {
    if (disabled) return;
    const nextIndex = vehicles.length + 1;
    const newVehicle: VehicleItem = {
      id: `V-${String(nextIndex).padStart(2, "0")}`,
      label: `Kendaraan ${nextIndex}`,
      capacityUnits: 500,
      available: true,
    };
    const next = [...vehicles, newVehicle];
    setVehicles(next);
    emitChange(next, warehouses);
  };

  // Inline vehicle name edit
  const startEditVehicle = (id: string, currentLabel: string) => {
    if (disabled) return;
    setEditingVehicleId(id);
    setEditingVehicleName(currentLabel);
  };

  const saveVehicleName = (id: string) => {
    const trimmed = editingVehicleName.trim();
    setEditingVehicleId(null);
    if (!trimmed) return;
    const next = vehicles.map((v) => (v.id === id ? { ...v, label: trimmed } : v));
    setVehicles(next);
    emitChange(next, warehouses);
  };

  // Update Vehicle (capacity or availability)
  const updateVehicle = (id: string, update: Partial<VehicleItem>) => {
    const next = vehicles.map((v) => (v.id === id ? { ...v, ...update } : v));
    setVehicles(next);
    emitChange(next, warehouses);
  };

  return (
    <div className="mx-auto grid w-full max-w-[1456px] items-start gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] xl:gap-8">
      {/* PERSEDIAAN GUDANG */}
      <section aria-labelledby="warehouse-title">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="warehouse-title" className="text-[20px] font-bold text-primary-dark md:text-[22px]">
            PERSEDIAAN GUDANG
          </h2>
          <button
            type="button"
            disabled={disabled}
            onClick={addWarehouse}
            aria-label="Tambah gudang"
            title="Tambah gudang baru"
            className="grid h-9 w-9 place-items-center rounded-full bg-primary-dark text-white shadow-sm transition hover:brightness-110 active:scale-95 disabled:opacity-50"
          >
            <Plus className="h-5 w-5 text-white" aria-hidden="true" />
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {warehouses.map((warehouse, warehouseIndex) => (
            <article key={warehouse.id} className="overflow-hidden rounded-[22px] border border-outline/40 bg-white shadow-sm">
              <header
                className={`flex h-[48px] items-center justify-between px-4 text-white ${warehouseHeaderColors[warehouseIndex % warehouseHeaderColors.length]}`}
              >
                {editingWarehouseId === warehouse.id ? (
                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      autoFocus
                      value={editingWarehouseName}
                      onChange={(e) => setEditingWarehouseName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveWarehouseName(warehouse.id);
                        if (e.key === "Escape") setEditingWarehouseId(null);
                      }}
                      onBlur={() => saveWarehouseName(warehouse.id)}
                      className="h-7 w-28 rounded bg-white/20 px-2 text-sm font-bold text-white placeholder:text-white/60 focus:bg-white/30 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => saveWarehouseName(warehouse.id)}
                      aria-label="Simpan nama gudang"
                      className="grid size-6 place-items-center rounded bg-white/20 hover:bg-white/30"
                    >
                      <Check className="size-3.5 text-white" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h3 className="text-[16px] font-bold md:text-[17px]">{warehouse.name}</h3>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => startEditWarehouse(warehouse.id, warehouse.name)}
                      aria-label={`Ubah nama ${warehouse.name}`}
                      title="Ubah nama gudang"
                      className="rounded p-0.5 opacity-75 transition hover:bg-white/20 hover:opacity-100 disabled:opacity-50"
                    >
                      <Pencil className="h-3.5 w-3.5 text-white" aria-hidden="true" />
                    </button>
                  </div>
                )}
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => addProductToWarehouse(warehouse.id)}
                  aria-label={`Tambah produk ke ${warehouse.name}`}
                  title="Tambah produk"
                  className="grid size-6 place-items-center rounded-full bg-white/20 text-white transition hover:bg-white/35 active:scale-95 disabled:opacity-50"
                >
                  <Plus className="h-4 w-4 text-white" aria-hidden="true" />
                </button>
              </header>
              <div className="space-y-2 p-3.5">
                {warehouse.items.map((item) => (
                  <div key={item.id} className="grid grid-cols-[1fr_72px] items-center gap-2">
                    {editingProduct?.warehouseId === warehouse.id && editingProduct?.productId === item.id ? (
                      <div className="flex items-center gap-1 min-w-0" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          autoFocus
                          value={editingProductName}
                          onChange={(e) => setEditingProductName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveProductName(warehouse.id, item.id);
                            if (e.key === "Escape") setEditingProduct(null);
                          }}
                          onBlur={() => saveProductName(warehouse.id, item.id)}
                          className="h-7 w-full min-w-0 rounded border border-primary/50 bg-white px-2 text-xs font-bold text-primary-dark focus:border-primary focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={() => saveProductName(warehouse.id, item.id)}
                          aria-label="Simpan nama produk"
                          className="grid size-6 shrink-0 place-items-center rounded bg-primary text-white hover:bg-primary-dark"
                        >
                          <Check className="size-3 text-white" />
                        </button>
                      </div>
                    ) : (
                      <div className="group/item flex items-center justify-between gap-1 min-w-0 pr-1">
                        <span className="truncate text-[13px] font-bold text-primary-dark" title={item.name}>
                          {item.name}
                        </span>
                        <button
                          type="button"
                          disabled={disabled}
                          onClick={() => startEditProduct(warehouse.id, item.id, item.name)}
                          aria-label={`Ubah nama ${item.name} di ${warehouse.name}`}
                          title="Ubah nama produk"
                          className="shrink-0 rounded p-0.5 opacity-60 transition group-hover/item:opacity-100 hover:bg-surface-low focus:opacity-100 disabled:opacity-0"
                        >
                          <Pencil className="h-3 w-3 text-primary/80 hover:text-primary" aria-hidden="true" />
                        </button>
                      </div>
                    )}
                    <input
                      type="number"
                      min={0}
                      disabled={disabled}
                      value={item.quantity}
                      aria-label={`Persediaan ${item.name} di ${warehouse.name}`}
                      onChange={(event) => updateInventory(warehouse.id, item.id, Number(event.target.value))}
                      className="h-8 w-full rounded-[8px] border border-outline bg-[#fafafa] px-2 text-right text-[14px] font-bold text-primary-dark focus:border-primary"
                    />
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* LIST KENDARAAN */}
      <section aria-labelledby="vehicle-title">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="vehicle-title" className="text-[20px] font-bold text-primary-dark md:text-[22px]">
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
            <article key={vehicle.id} className="rounded-[22px] bg-[#345173] p-4 text-white shadow-sm md:p-5">
              <div className="mb-2.5 flex items-center justify-between">
                {editingVehicleId === vehicle.id ? (
                  <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      autoFocus
                      value={editingVehicleName}
                      onChange={(e) => setEditingVehicleName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveVehicleName(vehicle.id);
                        if (e.key === "Escape") setEditingVehicleId(null);
                      }}
                      onBlur={() => saveVehicleName(vehicle.id)}
                      className="h-7 w-32 rounded bg-white/20 px-2 text-sm font-bold text-white placeholder:text-white/60 focus:bg-white/30 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => saveVehicleName(vehicle.id)}
                      aria-label="Simpan nama kendaraan"
                      className="grid size-6 place-items-center rounded bg-white/20 hover:bg-white/30"
                    >
                      <Check className="size-3.5 text-white" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-[15px] font-bold md:text-[16px]">{vehicle.label}</h3>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => startEditVehicle(vehicle.id, vehicle.label)}
                      aria-label={`Ubah nama ${vehicle.label}`}
                      title="Ubah nama kendaraan"
                      className="rounded p-0.5 opacity-75 transition hover:bg-white/20 hover:opacity-100 disabled:opacity-50"
                    >
                      <Pencil className="h-3.5 w-3.5 text-white" aria-hidden="true" />
                    </button>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={vehicle.available}
                    aria-label={`Status kendaraan ${vehicle.label}`}
                    disabled={disabled}
                    onClick={() => updateVehicle(vehicle.id, { available: !vehicle.available })}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${vehicle.available ? "bg-[#eba92d]" : "bg-white/30"}`}
                  >
                    <span
                      className={`pointer-events-none inline-block size-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${vehicle.available ? "translate-x-5" : "translate-x-0"}`}
                    />
                  </button>
                  <span className="text-[13px] font-bold md:text-[14px]">
                    {vehicle.available ? "Aktif" : "Non-Aktif"}
                  </span>
                </div>
              </div>
              <input
                type="number"
                min={1}
                disabled={disabled || !vehicle.available}
                value={vehicle.capacityUnits}
                placeholder={`Kapasitas ${vehicle.label}`}
                aria-label={`Kapasitas kendaraan ${vehicle.label}`}
                onChange={(event) =>
                  updateVehicle(vehicle.id, {
                    capacityUnits: Math.max(1, isNaN(Number(event.target.value)) ? 1 : Number(event.target.value)),
                  })
                }
                className="h-9 w-full rounded-[10px] border-0 bg-white px-4 text-[13px] font-medium text-black placeholder:text-gray-400 disabled:opacity-55 md:text-[14px]"
              />
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
