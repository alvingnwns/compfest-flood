# ResiliChain AI

ResiliChain AI is a flood-aware supply-chain recovery decision-support MVP with a Next.js frontend and FastAPI backend. The shared API contract is documented in [`docs/BACKEND_INTEGRATION_CONTRACT.md`](docs/BACKEND_INTEGRATION_CONTRACT.md).

## What is real and what is synthetic

The FastAPI API, Random Forest inference with `predict_proba`, NetworkX risk-aware routing, OR-Tools CP-SAT optimization, impact propagation, manufacturing/logistics/commerce decisions, and KPI calculations are executable computations. The active road snapshot is derived from OpenStreetMap. The active model is trained on Global Flood Database corridor labels across multiple Indonesian regions. March 2025 flood geometry and the company scenario remain transparent synthetic/simulated placeholders.

Phase D status: both Jakarta-only scientific attempts remain documented failures. Objective multi-region Indonesia discovery produced a feasible historical corridor-exposure dataset, and the selected model now runs offline over Jakarta as the deployment/demo pilot. Jakarta is not a labeled validation region; unseen-region recall is limited and Jakarta contains two unseen road categories. See [`docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md`](docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md), [`docs/FLOOD_RISK_MODEL_REPORT.md`](docs/FLOOD_RISK_MODEL_REPORT.md), and [`docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md`](docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md).

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
