import { CheckCircle2, Network, PackageCheck, RotateCcw, Truck, Warehouse } from "lucide-react";
import type { InventoryOverride, Scenario, VehicleOverride } from "@/domain/scenario";
import { OPERATIONAL_PRESETS, type OperationalOverrides, type OperationalPreset } from "./scenario-presets";

export function OperationalConditionPanel({
  scenario,
  selectedPresetId,
  overrides,
  custom,
  disabled,
  onSelect,
  onReset,
}: {
  scenario: Scenario;
  selectedPresetId: string;
  overrides: OperationalOverrides;
  custom: boolean;
  disabled?: boolean;
  onSelect: (preset: OperationalPreset) => void;
  onReset: () => void;
}) {
  const disabledVehicles = overrides.vehicleOverrides.filter((item: VehicleOverride) => item.available === false).length;
  const limitedCapacity = overrides.vehicleOverrides.filter((item: VehicleOverride) => item.capacityUnits !== undefined).length;
  const criticalInventory = overrides.inventoryOverrides.filter((item: InventoryOverride) => item.quantity <= 50).length;

  return (
    <section className="card flex flex-col p-5 md:p-6">
      <div className="mb-4 flex items-center justify-between gap-3 border-b border-outline pb-3">
        <div className="flex items-center gap-2">
          <Network className="text-primary" size={20} />
          <h2 className="section-title text-ink">2. Kondisi Operasional</h2>
        </div>
        {custom && <button type="button" onClick={onReset} disabled={disabled} className="inline-flex items-center gap-1 text-xs text-primary hover:underline"><RotateCcw size={12} /> Reset Normal</button>}
      </div>

      <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Kondisi operasional">
        {OPERATIONAL_PRESETS.map((preset) => {
          const selected = !custom && selectedPresetId === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={disabled}
              onClick={() => onSelect(preset)}
              className={`min-h-[108px] rounded-lg border p-3 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${selected ? "border-primary bg-primary/10" : "border-outline bg-surface hover:bg-surface-high"}`}
            >
              <span className="flex items-center justify-between gap-2">
                <strong className="text-sm text-ink">{preset.label}</strong>
                {selected && <CheckCircle2 size={16} className="text-primary" />}
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-muted">{preset.description}</span>
            </button>
          );
        })}
      </div>

      {custom && <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">Kondisi operasional disesuaikan melalui panel konfigurasi.</div>}

      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Status icon={Truck} label="Kendaraan" value={`${scenario.vehicles.length - disabledVehicles}/${scenario.vehicles.length} tersedia${limitedCapacity > 0 ? " · kapasitas dibatasi" : ""}`} />
        <Status icon={Warehouse} label="Persediaan" value={criticalInventory > 0 ? `${criticalInventory} stok kritis` : "Persediaan normal"} />
        <Status icon={PackageCheck} label="Pesanan" value={`${scenario.orders.length} pesanan aktif`} />
      </div>
    </section>
  );
}

function Status({ icon: Icon, label, value }: { icon: typeof Truck; label: string; value: string }) {
  return <div className="rounded-lg border border-outline/60 bg-surface-low p-3 text-center"><div className="eyebrow mb-1 flex items-center justify-center gap-1"><Icon size={13} /> {label}</div><div className="text-xs font-semibold text-ink">{value}</div></div>;
}
