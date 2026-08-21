/**
 * Curated product scenario & operational presets for the ARUNA demo.
 *
 * Architecture notes:
 * - Hazard Scenarios and Operational Conditions are strictly separated.
 * - Hazard Scenario: Banjir Jakarta — 04 Mar 2025 (historical flood ML + real OSM roads).
 * - Operational Condition: Business state presets (vehicle availability, capacity, inventory).
 */

import type { InventoryOverride, RainfallScenario, VehicleOverride } from "@/domain/scenario";

export type HazardScenario = {
  id: string;
  name: string;
  badge: "HISTORIS";
  location: string;
  eventType: string;
  mode: string;
  description: string;
};

export type OperationalOverrides = {
  vehicleOverrides: VehicleOverride[];
  inventoryOverrides: InventoryOverride[];
};

export type OperationalPreset = {
  id: string;
  label: string;
  badge: "DEFAULT" | "MODERAT" | "SEDANG" | "TINGGI";
  description: string;
  overrides: OperationalOverrides;
};

export type RainfallScenarioOption = {
  id: RainfallScenario;
  label: string;
  description: string;
};

export const RAINFALL_SCENARIOS: RainfallScenarioOption[] = [
  { id: "Q1", label: "Pola Hujan Relatif Rendah", description: "Curah hujan cenderung rendah dan stabil, sehingga potensi gangguan akibat hujan relatif kecil." },
  { id: "Q2", label: "Pola Hujan Menengah", description: "Curah hujan berada pada tingkat sedang dengan peningkatan intensitas yang mulai perlu diperhatikan." },
  { id: "Q3", label: "Pola Hujan Meningkat", description: "Curah hujan semakin tinggi dan dapat meningkatkan potensi gangguan serta risiko banjir di wilayah terdampak." },
  { id: "Q4", label: "Pola Hujan Tinggi dan Persisten", description: "Curah hujan tinggi berlangsung terus-menerus, dapat meningkatkan risiko banjir serta gangguan pada jalan." },
];

export function getRainfallScenario(id?: RainfallScenario): RainfallScenarioOption | undefined {
  return RAINFALL_SCENARIOS.find((scenario) => scenario.id === id);
}

export const HAZARD_SCENARIOS: HazardScenario[] = [
  {
    id: "scenario-jakarta-20250304",
    name: "Banjir Jakarta — 04 Mar 2025",
    badge: "HISTORIS",
    location: "Jakarta",
    eventType: "Banjir Perkotaan",
    mode: "Pemutaran Ulang Historis",
    description:
      "Pemutaran ulang skenario banjir perkotaan Jakarta 4 Maret 2025. Estimasi paparan koridor jalan dihasilkan oleh model historis ARUNA pada jaringan jalan OpenStreetMap.",
  },
];

export const OPERATIONAL_PRESETS: OperationalPreset[] = [
  {
    id: "normal",
    label: "Normal",
    badge: "DEFAULT",
    description: "Kondisi operasional awal tanpa pembatasan armada maupun persediaan gudang.",
    overrides: {
      vehicleOverrides: [],
      inventoryOverrides: [],
    },
  },
  {
    id: "limited-vehicle",
    label: "Kendaraan Terbatas",
    badge: "MODERAT",
    description:
      "Satu kendaraan distribusi (V-03) tidak tersedia. Sistem mengalokasikan ulang pengiriman ke armada yang tersisa.",
    overrides: {
      vehicleOverrides: [{ id: "V-03", available: false }],
      inventoryOverrides: [],
    },
  },
  {
    id: "critical-stock",
    label: "Stok Gudang Kritis",
    badge: "SEDANG",
    description:
      "Persediaan awal Produk A pada Gudang Timur dan Gudang Barat dikurangi signifikan (masing-masing 50 unit). Sistem menyesuaikan alokasi gudang dan memprioritaskan komposisi produksi.",
    overrides: {
      vehicleOverrides: [],
      inventoryOverrides: [
        { facilityId: "wh-east", productId: "prod-a", quantity: 50 },
        { facilityId: "wh-west", productId: "prod-a", quantity: 50 },
      ],
    },
  },
  {
    id: "severe-disruption",
    label: "Gangguan Operasional",
    badge: "TINGGI",
    description:
      "Dua kendaraan distribusi (V-01 dan V-02) tidak tersedia bersamaan dengan pengosongan persediaan Produk A di Gudang Timur (0 unit).",
    overrides: {
      vehicleOverrides: [
        { id: "V-01", available: false },
        { id: "V-02", available: false },
      ],
      inventoryOverrides: [{ facilityId: "wh-east", productId: "prod-a", quantity: 0 }],
    },
  },
];

export const DEFAULT_OPERATIONAL_PRESET = OPERATIONAL_PRESETS[0];

export function getOperationalPreset(id: string): OperationalPreset {
  return OPERATIONAL_PRESETS.find((p) => p.id === id) ?? DEFAULT_OPERATIONAL_PRESET;
}
