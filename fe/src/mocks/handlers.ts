import { delay, http, HttpResponse } from "msw";
import { recoveryGenerationRequestSchema } from "@/domain/recovery";
import { copilotRequestSchema } from "@/domain/copilot";
import type { DisruptionAnalysis } from "@/domain/disruption";
import { runSimulationRequestSchema, type Simulation } from "@/domain/scenario";
import { disruptionFixture, impactFixture, recoveryFixture, scenarioFixture, simulationFixture } from "./data";

const latency = () => delay(process.env.NODE_ENV === "test" ? 0 : 350);
const error = (status: number, code: string, message: string, retryable = false) => HttpResponse.json({ code, message, retryable }, { status });
const simulations = new Map<string, Simulation>([[simulationFixture.id, simulationFixture]]);
const relativeHazard = { Q1: 0.15, Q2: 0.46, Q3: 0.65, Q4: 0.73 } as const;

function mockIdentity(value: unknown): string {
  return Array.from(JSON.stringify(value)).reduce((checksum, character) => ((checksum * 31) + character.charCodeAt(0)) >>> 0, 0).toString(36);
}

function fuseRisk(staticRisk: number, hazardIndex: number): number {
  const clipped = Math.min(Math.max(staticRisk, 1e-9), 1 - 1e-9);
  const logit = Math.log(clipped / (1 - clipped));
  return 1 / (1 + Math.exp(-(logit + 1.5 * hazardIndex)));
}

function routingBand(score: number): "low" | "medium" | "high" | "critical" {
  if (score < 0.25) return "low";
  if (score < 0.5) return "medium";
  if (score < 0.75) return "high";
  return "critical";
}

function disruptionFor(simulation: Simulation): DisruptionAnalysis {
  if (simulation.analysisMode === "historical-replay" || simulation.hazard === undefined) return { ...disruptionFixture, simulationId: simulation.id };
  return {
    ...disruptionFixture,
    simulationId: simulation.id,
    roads: disruptionFixture.roads.map((road) => {
      const dynamicRoadRiskScore = fuseRisk(road.riskProbability, simulation.hazard!.relativeHazardIndex);
      return {
        ...road,
        dynamicRoadRiskScore,
        riskLevel: routingBand(dynamicRoadRiskScore),
        dynamicRiskScoreSemantics: "scenario-conditioned relative road-risk score; not a calibrated probability",
        routingBandBasis: "unchanged static-model thresholds used only for routing compatibility",
      };
    }),
  };
}

export const handlers = [
  http.get("*/api/scenarios/historical-jakarta", async () => { await latency(); return HttpResponse.json(scenarioFixture); }),
  http.post("*/api/simulations", async ({ request }) => {
    await latency();
    const body = runSimulationRequestSchema.safeParse(await request.json().catch(() => null));
    if (!body.success) return error(422, "validation_error", "The simulation request is invalid.");
    if (body.data.scenarioId !== scenarioFixture.id) return error(404, "scenario_not_found", "Scenario not found.");
    if (body.data.analysisMode === "historical-replay") return HttpResponse.json(simulationFixture, { status: 201 });
    const suffix = `${body.data.rainfallScenario}-${mockIdentity({ vehicleOverrides: body.data.vehicleOverrides ?? [], inventoryOverrides: body.data.inventoryOverrides ?? [] })}`;
    const simulation: Simulation = {
      ...simulationFixture,
      id: `${simulationFixture.id}-${suffix}`,
      analysisMode: "scenario-simulation",
      hazard: {
        rainfallScenario: body.data.rainfallScenario,
        temporalHazardScore: relativeHazard[body.data.rainfallScenario] * 0.45,
        relativeHazardIndex: relativeHazard[body.data.rainfallScenario],
        probabilityCalibrated: false,
        modelVersion: "temporal-hazard-v1",
        modelType: "random_forest_regressor",
        fusionMethod: "logit_shift",
        fusionBeta: 1.5,
        riskLevelSemantics: "routing compatibility band from unchanged static-model thresholds",
      },
    };
    simulations.set(simulation.id, simulation);
    return HttpResponse.json(simulation, { status: 201 });
  }),
  http.get("*/api/simulations/:id", async ({ params }) => { await latency(); const simulation = simulations.get(String(params.id)); return simulation ? HttpResponse.json(simulation) : error(404, "simulation_not_found", "Simulasi tidak ditemukan."); }),
  http.get("*/api/simulations/:id/disruption", async ({ params }) => { await latency(); const simulation = simulations.get(String(params.id)); return simulation ? HttpResponse.json(disruptionFor(simulation)) : error(404, "disruption_not_found", "Analisis gangguan tidak tersedia."); }),
  http.post("*/api/simulations/:id/recovery", async ({ params, request }) => {
    await latency();
    const body = recoveryGenerationRequestSchema.safeParse(await request.json().catch(() => null));
    if (!body.success) return error(422, "validation_error", "The recovery request is invalid.");
    return simulations.has(String(params.id)) ? HttpResponse.json({ ...recoveryFixture, simulationId: String(params.id) }, { status: 201 }) : error(404, "simulation_not_found", "Simulasi tidak ditemukan.");
  }),
  http.get("*/api/simulations/:id/recovery", async ({ params }) => { await latency(); return simulations.has(String(params.id)) ? HttpResponse.json({ ...recoveryFixture, simulationId: String(params.id) }) : error(404, "recovery_not_found", "Rencana pemulihan tidak tersedia."); }),
  http.get("*/api/simulations/:id/impact", async ({ params }) => { await latency(); return simulations.has(String(params.id)) ? HttpResponse.json({ ...impactFixture, simulationId: String(params.id) }) : error(404, "impact_not_found", "Perbandingan dampak tidak tersedia."); }),
  http.post("*/api/simulations/:id/copilot", async ({ params, request }) => {
    await latency();
    if (!simulations.has(String(params.id))) return error(404, "simulation_not_found", "Simulasi tidak ditemukan.");
    const body = copilotRequestSchema.safeParse(await request.json().catch(() => null));
    if (!body.success) return error(422, "validation_error", "Pertanyaan Copilot tidak valid.");
    return HttpResponse.json({
      answer: `Berdasarkan simulasi saat ini: ${body.data.message} Jawaban ini hanya menjelaskan hasil yang sudah dihitung.`,
      provider: "deterministic",
      grounded: true,
      suggestedQuestions: ["Why was this route chosen?", "Which orders remain at risk?"],
      fallbackReason: "mock_mode",
    });
  }),
];
