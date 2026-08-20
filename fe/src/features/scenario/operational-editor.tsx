import { Pencil, Plus } from "lucide-react";
import type { Scenario, VehicleOverride } from "@/domain/scenario";
import type { OperationalOverrides } from "./scenario-presets";

type Props = {
  scenario: Scenario;
  overrides: OperationalOverrides;
  disabled?: boolean;
  onChange: (overrides: OperationalOverrides) => void;
};

const warehouseHeaderColors = [
  "bg-[#633695]",
  "bg-[#39863e]",
  "bg-[#9c2a5d]",
  "bg-[#be6d12]",
];

export function OperationalEditor({ scenario, overrides, disabled, onChange }: Props) {
  const vehicleMap = Object.fromEntries(overrides.vehicleOverrides.map((item) => [item.id, item]));
  const inventoryMap = Object.fromEntries(overrides.inventoryOverrides.map((item) => [`${item.facilityId}:${item.productId}`, item]));
  const products = Object.fromEntries(scenario.products.map((product) => [product.id, product]));
  const warehouses = scenario.facilities.filter((facility) => facility.kind === "warehouse");

  const updateVehicle = (id: string, update: Partial<VehicleOverride>) => {
    const next = overrides.vehicleOverrides.filter((item) => item.id !== id);
    onChange({ ...overrides, vehicleOverrides: [...next, { ...vehicleMap[id], id, ...update }] });
  };

  const updateInventory = (facilityId: string, productId: string, quantity: number) => {
    const key = `${facilityId}:${productId}`;
    const next = overrides.inventoryOverrides.filter((item) => `${item.facilityId}:${item.productId}` !== key);
    onChange({ ...overrides, inventoryOverrides: [...next, { facilityId, productId, quantity: Math.max(0, quantity) }] });
  };

  return (
    <div className="mx-auto grid w-full max-w-[1456px] items-start gap-12 xl:grid-cols-[minmax(0,766px)_minmax(0,629px)] xl:gap-[61px]">
      <section aria-labelledby="warehouse-title">
        <h2 id="warehouse-title" className="mb-6 text-[24px] font-bold text-primary-dark md:text-[32px]">PERSEDIAAN GUDANG</h2>
        <div className="grid gap-6 sm:grid-cols-2">
          {warehouses.map((warehouse, warehouseIndex) => {
            const items = scenario.inventory.filter((item) => item.facilityId === warehouse.id);
            return (
              <article key={warehouse.id} className="min-h-[235px] overflow-hidden rounded-[33px] bg-white shadow-[0_0_7px_rgb(0_0_0/25%)]">
                <header
                  className={`flex h-[73px] items-center gap-3 px-6 text-white ${warehouseHeaderColors[warehouseIndex % warehouseHeaderColors.length]}`}
                >
                  <h3 className="text-[22px] font-bold md:text-[25px]">{warehouse.name || `Gudang ${warehouseIndex + 1}`}</h3>
                  <Pencil className="h-4 w-4 opacity-50" aria-hidden="true" />
                </header>
                <div className="space-y-3 p-5">
                  {items.map((item) => {
                    const key = `${item.facilityId}:${item.productId}`;
                    const quantity = inventoryMap[key]?.quantity ?? item.quantity;
                    return (
                      <label key={key} className="grid grid-cols-[1fr_92px] items-center gap-3">
                        <span className="min-w-0 text-[14px] font-semibold text-primary-dark">
                          <span className="block truncate">{products[item.productId]?.name ?? item.productId}</span>
                          <span className="text-[11px] font-medium text-muted">{item.unit}</span>
                        </span>
                        <input
                          type="number"
                          min={0}
                          disabled={disabled}
                          value={quantity}
                          aria-label={`Persediaan ${products[item.productId]?.name ?? item.productId} di ${warehouse.name}`}
                          onChange={(event) => updateInventory(item.facilityId, item.productId, Number(event.target.value))}
                          className="h-10 w-full rounded-[12px] border border-outline bg-[#fafafa] px-3 text-right text-sm font-semibold text-primary-dark focus:border-primary"
                        />
                      </label>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="vehicle-title">
        <div className="mb-1 flex h-[50px] items-center justify-between">
          <h2 id="vehicle-title" className="text-[24px] font-bold text-primary-dark md:text-[32px]">LIST KENDARAAN</h2>
          <button type="button" disabled title="Kendaraan mengikuti skenario aktif" aria-label="Tambah kendaraan" className="grid h-[50px] w-[50px] place-items-center rounded-full bg-primary opacity-100 shadow-sm disabled:cursor-not-allowed">
            <Plus className="h-8 w-8 text-white" aria-hidden="true" />
          </button>
        </div>
        <div className="space-y-3">
          {scenario.vehicles.map((vehicle, index) => {
            const override = vehicleMap[vehicle.id];
            const available = override?.available ?? vehicle.available;
            const capacity = override?.capacityUnits ?? vehicle.capacityUnits;
            return (
              <article key={vehicle.id} className="grid min-h-[129px] grid-cols-[minmax(0,1fr)_auto] items-center gap-5 rounded-[33px] bg-primary px-7 py-5 text-white md:px-10">
                <div className="min-w-0">
                  <div className="mb-2 flex items-center gap-2">
                    <h3 className="truncate text-[20px] font-semibold md:text-[21px]">{vehicle.label || `Kendaraan ${index + 1}`}</h3>
                    <Pencil className="h-4 w-4 opacity-50" aria-hidden="true" />
                  </div>
                  <input
                    type="number"
                    min={1}
                    disabled={disabled || !available}
                    value={capacity}
                    aria-label={`Kapasitas kendaraan ${vehicle.label}`}
                    onChange={(event) => updateVehicle(vehicle.id, { capacityUnits: Math.max(1, Number(event.target.value)) })}
                    className="h-11 w-full max-w-[284px] rounded-[15px] border-0 bg-[#fafafa] px-5 text-[16px] text-black placeholder:text-black/45 disabled:opacity-55 md:text-[18px]"
                  />
                </div>
                <div className="flex min-w-[118px] flex-col items-center gap-2">
                  <span className="text-[17px] font-semibold md:text-[20px]">{available ? "Aktif" : "Non-Aktif"}</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={available}
                    aria-label={`Status kendaraan ${vehicle.label}`}
                    disabled={disabled}
                    onClick={() => updateVehicle(vehicle.id, { available: !available })}
                    className={`relative h-8 w-[52px] rounded-full border-2 border-white transition ${available ? "bg-white/35" : "bg-primary-dark"}`}
                  >
                    <span className={`absolute top-[3px] h-[22px] w-[22px] rounded-full bg-white shadow transition ${available ? "left-[25px]" : "left-[3px]"}`} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
