import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { AnalysisMode, RainfallScenario } from "@/domain/scenario";
import { scenarioFixture } from "@/mocks/data";
import { AnalysisModePanel } from "./analysis-mode-panel";
import { OperationalConditionPanel } from "./operational-condition-panel";
import { OPERATIONAL_PRESETS } from "./scenario-presets";

function Harness() {
  const [mode, setMode] = useState<AnalysisMode>("historical-replay");
  const [rainfall, setRainfall] = useState<RainfallScenario>();
  const [preset, setPreset] = useState(OPERATIONAL_PRESETS[0]);
  return <>
    <output data-testid="selection">{mode}|{rainfall ?? "none"}|{preset.id}</output>
    <AnalysisModePanel analysisMode={mode} rainfallScenario={rainfall} onModeChange={setMode} onRainfallChange={setRainfall} />
    <OperationalConditionPanel scenario={scenarioFixture} selectedPresetId={preset.id} overrides={preset.overrides} custom={false} onSelect={setPreset} onReset={() => setPreset(OPERATIONAL_PRESETS[0])} />
  </>;
}

describe("dynamic scenario controls", () => {
  it("defaults to historical replay and hides temporal controls", () => {
    render(<Harness />);
    expect(screen.getByTestId("selection")).toHaveTextContent("historical-replay|none|normal");
    expect(screen.getByText("Jakarta · 04 Mar 2025")).toBeInTheDocument();
    expect(screen.queryByText("Pola Curah Hujan")).not.toBeInTheDocument();
  });

  it("switches mode, maps Q3, and keeps operational selection independent", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("radio", { name: /Simulasi Kondisi/ }));
    expect(screen.getByText("Pola Curah Hujan")).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Pola Hujan Meningkat/ }));
    await user.click(screen.getByRole("radio", { name: /Stok Gudang Kritis/ }));
    expect(screen.getByTestId("selection")).toHaveTextContent("scenario-simulation|Q3|critical-stock");
    expect(screen.getByText("Pola Hujan Meningkat")).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toContain("probabilitas jalan");
  });
});
