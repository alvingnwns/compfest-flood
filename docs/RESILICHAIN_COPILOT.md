# ResiliChain Copilot

## Purpose

ResiliChain Copilot is a grounded conversational explanation layer for the current ResiliChain simulation. It answers operational questions about already-computed disruption, routing, recovery, and KPI results.

ResiliChain Copilot explains and interrogates already-computed simulation results. It does not perform route optimization or replace OR-Tools decisions.

## Architecture

```text
Historical Random Forest + optional Dynamic Hazard
→ Jakarta OSM graph
→ NetworkX routing
→ OR-Tools recovery optimization
→ Manufacturing / Logistics / Commerce outcomes
→ computed KPIs
→ compact CopilotContext
→ Gemini 3.5 Flash
→ Qwen3.5-Flash via OpenRouter when Gemini is unavailable
→ deterministic grounded fallback when unavailable
→ /copilot
```

The Copilot layer runs after the computational pipeline. It cannot change route selection, production quantities, warehouse or vehicle assignments, order priority, fulfillment decisions, optimizer output, or KPI values.

## API

`POST /api/simulations/{simulationId}/copilot`

```json
{
  "message": "Why was this route selected?",
  "recentMessages": [
    { "role": "user", "content": "Explain the recovery plan." }
  ]
}
```

Only the six most recent messages are accepted. Conversation history is supplied by the frontend and is not persisted.

The response identifies whether Gemini, Qwen, or the deterministic provider answered, always marks the response as grounded, and may include a safe fallback-reason code.

## CopilotContext

Only compact, existing simulation evidence is supplied:

- simulation ID, scenario ID/name, analysis mode, region, model version, and optimizer version;
- Dynamic Hazard scenario, relative index, temporal score, calibration flag, and safe semantics when active;
- up to 12 highest-risk affected roads, their relative/historical score semantics, risk bands, and affected entity IDs;
- computed baseline/recovery routes, endpoints, ETA, exposure band/score, and affected segments;
- impacted supplier, warehouse, and order identifiers/names;
- road segments at risk, disruption sales exposure, and prioritized issues;
- recovery status and summary;
- bounded Manufacturing, Logistics, and Commerce What / Why / Expected Impact actions;
- existing Before/After KPI values and units.

Raw geometries, source code, model artifacts, credentials, and the complete application state are not sent.

## Grounding

The provider prompt requires answers only from `CopilotContext`, prohibits invented numbers and decisions, and requires an explicit unavailable response when evidence is absent. Gemini output is constrained to a JSON schema; Qwen output is locally validated. Missing, empty, or malformed output advances safely to the next provider.

The deterministic provider answers common route, supplier, order, bottleneck, trade-off, recovery, Dynamic Hazard, and KPI questions directly from the same context. It refuses unrelated or future-weather questions.

## Response Policy

- Default answers are executive-first, direct, and normally limited to 120 words.
- Technical engine details, exact scores, OSM segments, and internal IDs appear only when explicitly requested.
- A deterministic language rule makes Gemini, Qwen, and deterministic fallback match English or Bahasa Indonesia questions.
- Default output uses human-readable names and suppresses database-like identifiers.
- Responses are clean plain text; the frontend does not require a Markdown dependency.
- Historical risk uses estimated road-corridor exposure language. Dynamic Hazard remains a relative what-if scenario, not live weather or a calibrated probability.
- Every numerical claim must come from the current compact `CopilotContext` and be material to the question.
- Operational recommendations such as monitoring are prohibited unless they are explicit simulation evidence.
- Trade-offs are stated only when baseline/recovery values or recorded actions show a material downside.

## Provider configuration

Backend-only variables in `be/.env`:

```dotenv
EXPLANATION_MODE=auto
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_QWEN_MODEL=qwen/qwen3.5-flash-02-23
```

Gemini uses the official `google-genai` Python SDK 2.x with one request attempt, a 30-second timeout, and structured JSON output. Qwen uses OpenRouter's OpenAI-compatible chat-completions endpoint with grounded plain-text output and local validation. Neither provider silently changes its configured model. Set `EXPLANATION_MODE=deterministic` to bypass both remote providers explicitly.

## Provider fallback

Current order:

```text
Gemini → Qwen via OpenRouter → deterministic grounded provider
```

The runtime order is Gemini, then Qwen3.5-Flash through OpenRouter, then the deterministic grounded provider. Qwen is attempted only when Gemini is unavailable or fails, without changing simulation computation.

Gemini and OpenRouter timeout, quota exhaustion, model unavailability, malformed output, missing key, and other provider errors safely advance to the next provider with a non-secret reason code. There is no long retry loop.

## Offline behavior

Historical Replay, Dynamic Hazard, NetworkX, OR-Tools, and KPI computation remain local and independent of both remote providers. When remote providers are unavailable, Copilot uses deterministic simulation explanations. No key is required for core ResiliChain.

## Security

- `GEMINI_API_KEY` and `OPENROUTER_API_KEY` are loaded only by backend `pydantic-settings` as secret values.
- `be/.env` is ignored by Git.
- The key is never returned by an API, logged, placed in a prompt, or included in frontend code.
- No `NEXT_PUBLIC_*` Gemini or OpenRouter variable exists.
- Tests force an empty key and mock the provider; they never call the live API.

## Scientific language

Historical road-risk wording must use **estimated flood exposure**, **road-corridor flood risk**, or **historical susceptibility**. It must not claim certain flooding or road closure.

Dynamic Hazard wording must use **relative hazard**, **relative road risk**, **what-if rainfall scenario**, **historical-derived rainfall pattern**, or **simulation condition**. It is not live weather, a calibrated flood probability, or a forecast.

## Limitations

- Answers are limited to the current process-local simulation.
- Conversation history is bounded and not persisted.
- Gemini and Qwen are optional enrichment; deterministic grounded answers remain available without either provider.
- Copilot does not have web search, live weather, database, write, routing, optimization, or tool-execution authority.
- Operator review remains required before acting on any simulation result.
