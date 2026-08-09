# ResiliChain FastAPI Backend Foundation

This directory contains the contract-compatible backend foundation for the completed ResiliChain frontend. It provides deterministic development implementations behind replaceable engine boundaries. It does **not** perform real AI inference, real road-network routing, or mathematical optimization.

The source of truth is [`../docs/BACKEND_INTEGRATION_CONTRACT.md`](../docs/BACKEND_INTEGRATION_CONTRACT.md).

## Architecture

```text
FastAPI routes
  -> application services
  -> engine protocols and repository interfaces
  -> local JSON fixtures + process-local simulation repository
```

- `app/api`: thin HTTP handlers.
- `app/schemas`: Pydantic models matching frontend Zod schemas.
- `app/services`: simulation, disruption, recovery, and impact orchestration.
- `app/engines`: replaceable flood-risk, routing, impact, and optimizer boundaries.
- `app/repositories`: trusted local fixture loading and in-memory state.
- `data`: deterministic Jakarta scenario and development engine outputs.
- `tests`: endpoint, error, contract-flow, geometry, bounds, and referential-integrity tests.

## Requirements

- Python 3.11+

## Local setup

```bash
cd be
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment |
| `HOST` | `0.0.0.0` | Documented server bind host |
| `PORT` | `8000` | Documented server port |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Explicit CORS origin |
| `DATA_DIR` | `be/data` | Trusted local fixture directory |
| `ENGINE_MODE` | `stub` | Development engine implementation |

No third-party API credentials are required.

## Commands

```bash
python -m pytest
ruff check .
ruff format --check .
python -c "from app.main import app; print(app.title)"
```

## API endpoints

- `GET /health`
- `GET /api/scenarios/historical-jakarta`
- `POST /api/simulations`
- `GET /api/simulations/{simulationId}`
- `GET /api/simulations/{simulationId}/disruption`
- `POST /api/simulations/{simulationId}/recovery`
- `GET /api/simulations/{simulationId}/recovery`
- `GET /api/simulations/{simulationId}/impact`

## Stub engine replacement

- Replace `StubFloodRiskEngine` with a trained implementation of `FloodRiskEngine`.
- Replace `StubRoutingEngine` with an OSMnx/NetworkX implementation of `RoutingEngine`.
- Replace `StubImpactEngine` with production dependency/impact evaluation.
- Replace `StubRecoveryOptimizer` with an OR-Tools implementation of `RecoveryOptimizer`.

The dependency container is the only composition point that needs to select new implementations. API routes and frontend contracts remain unchanged.

## Current persistence and idempotency

Scenario and development outputs are local JSON files. Simulation and recovery state are stored in memory and reset whenever the backend restarts. Repeating a simulation request for the same scenario within one process returns the existing completed simulation; repeating recovery generation returns the existing plan. There is no cross-process idempotency guarantee.

## Frontend integration

Start the backend, then configure `fe/.env.local`:

```dotenv
NEXT_PUBLIC_DATA_SOURCE=api
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Restart the frontend from `fe/`. No page or component changes are required.

## Docker

From the repository root:

```bash
docker compose up --build backend
```

This phase containerizes the backend only. The completed frontend continues to run with its existing Node.js workflow.

## Deliberate limitations

No database, authentication, job queue, WebSocket lifecycle, live BMKG/PetaBencana integration, trained ML, OSMnx/NetworkX route calculation, or OR-Tools optimization is included in this foundation.
