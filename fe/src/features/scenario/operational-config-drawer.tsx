"use client";

import { Settings, X, RotateCcw, Check } from "lucide-react";
import { useState } from "react";
import type { InventoryOverride, Scenario, VehicleOverride } from "@/domain/scenario";
import type { OperationalOverrides, OperationalPreset } from "./scenario-presets";

type Props = {
  open: boolean;
  onClose: () => void;
  scenario: Scenario;
  preset: OperationalPreset;
  overrides: OperationalOverrides;
  onApply: (overrides: OperationalOverrides) => void;
};

type ValidationErrors = { [key: string]: string };

function validate(draft: OperationalOverrides): ValidationErrors {
  const errors: ValidationErrors = {};
  for (const ov of draft.vehicleOverrides) {
    if (ov.capacityUnits !== undefined && ov.capacityUnits <= 0) {
      errors[`cap-${ov.id}`] = "Kapasitas harus lebih dari 0.";
    }
  }
  for (const ov of draft.inventoryOverrides) {
    if (ov.quantity < 0) {
      errors[`inv-${ov.facilityId}-${ov.productId}`] = "Jumlah tidak boleh negatif.";
    }
  }
  return errors;
}

export function OperationalConfigDrawer({ open, onClose, scenario, preset, overrides, onApply }: Props) {
  const [draft, setDraft] = useState<OperationalOverrides>(overrides);
  const [errors, setErrors] = useState<ValidationErrors>({});

  if (!open) return null;

  const vehicleMap = Object.fromEntries(
    draft.vehicleOverrides.map((ov: VehicleOverride) => [ov.id, ov])
  );
  const inventoryMap = Object.fromEntries(
    draft.inventoryOverrides.map((ov: InventoryOverride) => [`${ov.facilityId}:${ov.productId}`, ov])
  );

  const updateVehicle = (id: string, update: { available?: boolean; capacityUnits?: number | undefined }) => {
    const existing = vehicleMap[id] ?? { id };
    const merged = { ...existing, ...update };
    const rest = draft.vehicleOverrides.filter((ov: VehicleOverride) => ov.id !== id);
    setDraft({ ...draft, vehicleOverrides: [...rest, merged] });
  };

  const updateInventory = (facilityId: string, productId: string, quantity: number) => {
    const key = `${facilityId}:${productId}`;
    const rest = draft.inventoryOverrides.filter(
      (ov: InventoryOverride) => `${ov.facilityId}:${ov.productId}` !== key
    );
    setDraft({ ...draft, inventoryOverrides: [...rest, { facilityId, productId, quantity }] });
  };

  const handleApply = () => {
    const errs = validate(draft);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setErrors({});
    onApply(draft);
    onClose();
  };

  const handleReset = () => {
    setDraft(preset.overrides);
    setErrors({});
  };

  const warehouses = scenario.facilities.filter((f) => f.kind === "warehouse");
  const products = Object.fromEntries(scenario.products.map((p) => [p.id, p]));
  const inventoryItems = scenario.inventory.filter((inv) =>
    warehouses.some((wh) => wh.id === inv.facilityId)
  );

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-ink/30 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Konfigurasi Data Operasional"
        className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col overflow-y-auto border-l border-outline bg-surface shadow-2xl"
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-outline bg-surface px-5 py-4">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-primary" />
            <span className="font-semibold text-ink">Atur Data Operasional</span>
          </div>
          <button
            onClick={onClose}
            aria-label="Tutup panel"
            className="rounded-md p-1 hover:bg-surface-high"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 space-y-6 px-5 py-5">
          {/* Info banner */}
          <div className="rounded-lg border border-secondary-soft bg-secondary-soft/30 p-3 text-xs text-muted">
            <strong className="text-ink">Data simulasi saja.</strong> Nilai di bawah mengubah kondisi operasional yang dikirim ke backend. Hanya kolom yang benar-benar digunakan oleh optimizer ditampilkan.
          </div>

          {/* Section: PEMASOK (read-only) */}
          <section>
            <SectionHeader title="Pemasok" />
            <div className="rounded-lg border border-outline bg-surface-low p-3 text-xs text-muted">
              Pengelolaan status pemasok belum tersedia sebagai input override. Data pemasok diambil langsung dari skenario.
            </div>
          </section>

          {/* Section: KENDARAAN */}
          <section>
            <SectionHeader title="Kendaraan" />
            <div className="space-y-3">
              {scenario.vehicles.map((vehicle) => {
                const ov = vehicleMap[vehicle.id];
                const isAvailable = ov?.available ?? vehicle.available;
                const cap = ov?.capacityUnits ?? vehicle.capacityUnits;
                const capKey = `cap-${vehicle.id}`;
                return (
                  <div key={vehicle.id} className="rounded-lg border border-outline bg-surface-low p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-medium text-ink">{vehicle.label}</span>
                      <button
                        role="switch"
                        aria-checked={isAvailable}
                        aria-label={`Status kendaraan ${vehicle.label}`}
                        onClick={() => updateVehicle(vehicle.id, { available: !isAvailable })}
                        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
                          isAvailable ? "bg-primary" : "bg-surface-highest"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
                            isAvailable ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted">
                      <span>{isAvailable ? "Aktif" : "Tidak Tersedia"}</span>
                    </div>
                    {isAvailable && (
                      <div className="mt-2">
                        <label className="eyebrow mb-1 block">Kapasitas (unit)</label>
                        <input
                          type="number"
                          min={1}
                          value={cap}
                          aria-label={`Kapasitas kendaraan ${vehicle.label}`}
                          onChange={(e) => updateVehicle(vehicle.id, { capacityUnits: Number(e.target.value) || 1 })}
                          className="w-full rounded border border-outline bg-surface px-2 py-1 text-sm focus:border-primary focus:outline-none"
                        />
                        {errors[capKey] && <p className="mt-1 text-xs text-danger">{errors[capKey]}</p>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Section: PERSEDIAAN */}
          <section>
            <SectionHeader title="Persediaan Gudang" />
            {inventoryItems.length === 0 ? (
              <p className="text-xs text-muted">Tidak ada data persediaan gudang.</p>
            ) : (
              <div className="space-y-2">
                {inventoryItems.map((inv) => {
                  const key = `${inv.facilityId}:${inv.productId}`;
                  const errKey = `inv-${inv.facilityId}-${inv.productId}`;
                  const ov = inventoryMap[key];
                  const qty = ov?.quantity ?? inv.quantity;
                  const facilityName = scenario.facilities.find((f) => f.id === inv.facilityId)?.name ?? inv.facilityId;
                  const productName = products[inv.productId]?.name ?? inv.productId;
                  return (
                    <div key={key} className="rounded-lg border border-outline bg-surface-low p-3">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-xs font-medium text-ink">{facilityName} — {productName}</span>
                        <span className="mono text-[10px] text-muted">{inv.unit}</span>
                      </div>
                      <input
                        type="number"
                        min={0}
                        value={qty}
                        aria-label={`Persediaan ${productName} di ${facilityName}`}
                        onChange={(e) => updateInventory(inv.facilityId, inv.productId, Number(e.target.value))}
                        className="w-full rounded border border-outline bg-surface px-2 py-1 text-sm focus:border-primary focus:outline-none"
                      />
                      {errors[errKey] && <p className="mt-1 text-xs text-danger">{errors[errKey]}</p>}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Note: recovery policy */}
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            <strong>Kebijakan Pemulihan</strong> (substitusi produk, batas keterlambatan) dikonfigurasi saat membuat rencana pemulihan — bukan di sini.
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 flex items-center justify-between border-t border-outline bg-surface px-5 py-4">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 rounded-lg border border-outline px-3 py-2 text-sm font-medium text-muted hover:bg-surface-high"
          >
            <RotateCcw size={14} />
            Kembalikan ke Default
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg border border-outline px-3 py-2 text-sm font-medium hover:bg-surface-high"
            >
              Batal
            </button>
            <button
              onClick={handleApply}
              className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary-dark"
            >
              <Check size={14} />
              Terapkan Perubahan
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="eyebrow mb-2 flex items-center gap-1.5 text-muted">
      {title}
    </div>
  );
}
