# ARUNA

Flood-aware supply-chain recovery decision support for manufacturing, logistics, and commerce.

## Overview

Flood disruption can expose critical road corridors, delay material and product movement, and force trade-offs between fulfillment, delivery time, and sales exposure. ARUNA turns a transparent Jakarta demonstration scenario into an end-to-end decision workflow: estimate corridor exposure, trace operational disruption, optimize a recovery plan, compare business impact, and explain the evidence behind the result.

ARUNA is an MVP for planning support. It does not claim certain flooding, live road closure, or operational execution authority.

## What ARUNA Does

```text
Scenario -> Disruption -> Recovery -> Impact -> Copilot
```

- **Scenario:** run the built-in historical replay or a historical-derived Dynamic Hazard what-if scenario; adjust inventory and fleet inputs or upload custom business data.
- **Disruption:** inspect estimated road-corridor flood exposure, affected orders, and pre-optimization risk-aware route candidates.
- **Recovery:** use OR-Tools to coordinate production, warehouse allocation, vehicles, routes, priorities, deadlines, and fulfillment.
- **Impact:** compare computed baseline and recovery KPIs, including legitimate trade-offs such as additional delay.
- **Copilot:** ask grounded questions about the current simulation, with a deterministic local fallback when remote providers are unavailable.

## Core Technology

- A committed Random Forest model trained on historical Global Flood Database road-corridor labels from multiple Indonesian regions
- An optional historical-derived Dynamic Hazard temporal what-if signal
- A compact OpenStreetMap-derived Jakarta road network
- NetworkX baseline and risk-aware route computation
- OR-Tools CP-SAT recovery optimization
- FastAPI backend and Next.js frontend

## AI and Model Semantics

The historical model uses committed road features to estimate **road-corridor flood exposure probability**. Its output is not guaranteed flooding or road-closure certainty. The selected Random Forest and its evaluation evidence are documented in [`docs/FLOOD_RISK_MODEL_REPORT.md`](docs/FLOOD_RISK_MODEL_REPORT.md) and [`docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md`](docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md).

Dynamic Hazard combines historical exposure with a frozen, historical-derived temporal signal for Q1-Q4 what-if analysis. It is not live weather, a calibrated flood probability, or a forecast. Research artifacts and the runtime contract are documented in [`be/docs/dynamic-hazard-runtime.md`](be/docs/dynamic-hazard-runtime.md) and [`be/artifacts/dynamic-hazard/experiments/`](be/artifacts/dynamic-hazard/experiments/).

## Quick Start with Docker

Prerequisite: Docker Desktop or Docker Engine with Docker Compose.

```bash
git clone https://github.com/alvingnwns/compfest-flood.git
cd compfest-flood
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- Scenario workflow: <http://localhost:3000/scenario>
- Backend: <http://localhost:8000>
- Health check: <http://localhost:8000/health>

Stop both services:

```bash
docker compose down
```

No host-side Node.js, Python, model service, or API key is required for this Docker flow.

## Environment Variables

### Required

None. Docker defaults run the complete core workflow with the local deterministic Copilot fallback.

### Optional

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_DATA_SOURCE` | `api` | Use `mock` only for isolated frontend development. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Browser-visible backend base URL. |
| `EXPLANATION_MODE` | `auto` | Use `deterministic` to bypass remote Copilot providers. |
| `GEMINI_API_KEY` | empty | Optional Gemini Copilot enrichment. |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model selection. |
| `OPENROUTER_API_KEY` | empty | Optional Qwen fallback through OpenRouter. |
| `OPENROUTER_BASE_URL` | provider endpoint | OpenRouter API base URL. |
| `OPENROUTER_QWEN_MODEL` | `qwen/qwen3.5-flash-02-23` | OpenRouter model selection. |

Copy placeholders from [`be/.env.example`](be/.env.example) and [`fe/.env.example`](fe/.env.example) when needed. Never commit real keys or local `.env` files.

## Demo Data

ARUNA includes a built-in fictional Nusantara Foods scenario. For the custom-data flow, open **Scenario -> Custom Business Data -> Download Template**. The backend generates `ARUNA_Business_Data_Template.xlsx`; replace its example rows, upload it, review the validation preview, and select **Gunakan Data** before running the scenario.

No separate workbook is required from the repository root. The template and importer use the same schema and are tested together. See [`docs/CUSTOM_BUSINESS_DATA.md`](docs/CUSTOM_BUSINESS_DATA.md).

## Current MVP Scope

- Jakarta is a predefined demonstration network and deployment pilot, not a labeled validation region.
- Gudang Barat and Gudang Timur are fixed facilities; inventory is editable, but adding or renaming warehouses is unsupported.
- Existing vehicles are configurable, and valid custom vehicles enter the effective scenario and optimizer.
- Custom workbooks replace products, prices, orders, inventory, materials, and BOM data while retaining the Jakarta facilities and network.
- Supplier-to-factory and warehouse-to-store legs are routed explicitly; factory-to-warehouse transfer remains an aggregate planning abstraction.
- Dynamic Hazard is a historical-derived what-if signal, not a live forecast.
- Simulation state, custom snapshots, idempotency, and Copilot context are process-local. There is no database, authentication, or tenancy boundary.

## Repository Structure

```text
be/         FastAPI application, models, data, research artifacts, scripts, and tests
fe/         Next.js application and frontend tests
docs/       API, data, model, routing, and business-data documentation
compose.yaml
README.md
```

## Reproducibility and Tests

Backend:

```bash
cd be
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Frontend:

```bash
cd fe
npm ci
npm test
npm run typecheck
npm run lint
npm run build
```

The runtime model, model metrics, OSM snapshot, and Dynamic Hazard artifacts are committed for offline reproducibility. Detailed backend computation and limitations are in [`be/README.md`](be/README.md).

## Competition

Prepared as ARUNA for COMPFEST AIC 2026.
