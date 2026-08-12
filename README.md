# ResiliChain AI

ResiliChain AI is a flood-aware supply-chain recovery decision-support MVP with a Next.js frontend and FastAPI backend. The shared API contract is documented in [`docs/BACKEND_INTEGRATION_CONTRACT.md`](docs/BACKEND_INTEGRATION_CONTRACT.md).

## What is real and what is synthetic

The FastAPI API, Logistic Regression inference with `predict_proba`, NetworkX risk-aware routing, OR-Tools CP-SAT optimization, impact propagation, manufacturing/logistics/commerce decisions, and KPI calculations are executable computations. The active road snapshot is derived from OpenStreetMap. The active model's training labels, March 2025 flood extent, and company scenario remain transparent synthetic placeholders.

Phase C status: real OSM is complete. Earth Engine processing was completed for Sentinel-1 and the Global Flood Database, but both scientific feasibility gates failed with zero canonical positive road/corridor labels. Historical model training was therefore prohibited. See [`docs/FLOOD_REMOTE_SENSING_PIPELINE.md`](docs/FLOOD_REMOTE_SENSING_PIPELINE.md) and [`docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md`](docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md).

## Run locally

Backend:

```powershell
cd be
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd fe
npm install
$env:NEXT_PUBLIC_DATA_SOURCE="api"
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

Open `http://localhost:3000/scenario`. Mock mode remains available through `NEXT_PUBLIC_DATA_SOURCE=mock`.

## Quality gates

```powershell
cd be
python -m pytest
python -m ruff check .
python -m ruff format --check .

cd ..\fe
npm run lint
npm run typecheck
npm test
npm run build
```

See [`be/README.md`](be/README.md) for computation rules, KPI formulas, Docker, and current limitations. Simulation and request-idempotency state is process-local and resets on backend restart.
