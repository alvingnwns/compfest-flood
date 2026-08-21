export type BusinessDataMode = "demo" | "custom";

export function showsEnvironmentalCondition(mode?: BusinessDataMode): boolean {
  return mode === "demo";
}

export function showsWeatherSimulation(mode?: BusinessDataMode): boolean {
  return mode !== undefined;
}

export function showsOperationalFlow(mode?: BusinessDataMode): boolean {
  return mode !== undefined;
}
