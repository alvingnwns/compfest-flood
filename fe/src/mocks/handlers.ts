import { delay, http, HttpResponse } from "msw";
import { recoveryGenerationRequestSchema } from "@/domain/recovery";
import { runSimulationRequestSchema } from "@/domain/scenario";
import { disruptionFixture, impactFixture, recoveryFixture, scenarioFixture, simulationFixture } from "./data";

const latency = () => delay(process.env.NODE_ENV === "test" ? 0 : 350);
const error = (status: number, code: string, message: string, retryable = false) => HttpResponse.json({ code, message, retryable }, { status });

export const handlers = [
  http.get("*/api/scenarios/historical-jakarta", async () => { await latency(); return HttpResponse.json(scenarioFixture); }),
  http.post("*/api/simulations", async ({ request }) => {
    await latency();
    const body = runSimulationRequestSchema.safeParse(await request.json().catch(() => null));
    if (!body.success) return error(422, "validation_error", "The simulation request is invalid.");
    if (body.data.scenarioId !== scenarioFixture.id) return error(404, "scenario_not_found", "Scenario not found.");
    return HttpResponse.json(simulationFixture, { status: 201 });
  }),
  http.get("*/api/simulations/:id", async ({ params }) => { await latency(); return params.id === simulationFixture.id ? HttpResponse.json(simulationFixture) : error(404, "simulation_not_found", "Simulasi tidak ditemukan."); }),
  http.get("*/api/simulations/:id/disruption", async ({ params }) => { await latency(); return params.id === simulationFixture.id ? HttpResponse.json(disruptionFixture) : error(404, "disruption_not_found", "Analisis gangguan tidak tersedia."); }),
  http.post("*/api/simulations/:id/recovery", async ({ params, request }) => {
    await latency();
    const body = recoveryGenerationRequestSchema.safeParse(await request.json().catch(() => null));
    if (!body.success) return error(422, "validation_error", "The recovery request is invalid.");
    return params.id === simulationFixture.id ? HttpResponse.json(recoveryFixture, { status: 201 }) : error(404, "simulation_not_found", "Simulasi tidak ditemukan.");
  }),
  http.get("*/api/simulations/:id/recovery", async ({ params }) => { await latency(); return params.id === simulationFixture.id ? HttpResponse.json(recoveryFixture) : error(404, "recovery_not_found", "Rencana pemulihan tidak tersedia."); }),
  http.get("*/api/simulations/:id/impact", async ({ params }) => { await latency(); return params.id === simulationFixture.id ? HttpResponse.json(impactFixture) : error(404, "impact_not_found", "Perbandingan dampak tidak tersedia."); }),
];
