# ARUNA

ARUNA is a flood-aware supply-chain recovery decision-support MVP with a Next.js frontend and FastAPI backend. The shared API contract is documented in [`docs/BACKEND_INTEGRATION_CONTRACT.md`](docs/BACKEND_INTEGRATION_CONTRACT.md).

## Quick Start with Docker

Prerequisites: Docker Desktop or Docker Engine with Docker Compose.

```powershell
git clone <repository-url>
cd <repository>
docker compose up --build
```

No environment file or API key is required for the core application. After both services start, open:

- Frontend: `http://localhost:3000`
- Scenario workflow: `http://localhost:3000/scenario`
- Backend API: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`

Stop the application with:

```powershell
docker compose down
```

### Environment variables

Core Docker defaults require no configuration. The frontend is built in API mode with the browser-visible backend URL `http://localhost:8000`; overrides may be supplied through the shell or a root `.env` file using `NEXT_PUBLIC_DATA_SOURCE` and `NEXT_PUBLIC_API_BASE_URL`.

`GEMINI_API_KEY` and `OPENROUTER_API_KEY` are optional Copilot provider keys. With neither key configured, ARUNA boots normally and Copilot uses its grounded deterministic fallback. Never commit real keys or local `.env` files.

## Custom business data

The Scenario page defaults to the built-in demo company snapshot. To use a custom business snapshot:

1. Select **Custom Business Data**.
2. Download `ARUNA_Business_Data_Template.xlsx`.
3. Replace the example rows with products, numeric IDR prices, orders, inventory, supplier-specific materials, and BOM relationships.
4. Upload the `.xlsx`, review the validation preview and total order value, then select **Gunakan Data**.
5. Run the normal simulation, recovery, Impact, and Copilot flow.

Custom operational data uses the same NetworkX, OR-Tools, and KPI path as demo mode. It continues to use ARUNA's Jakarta demo facilities, vehicles, coordinates, and logistics network. Snapshots are process-local, expire after two hours, and must be uploaded again after backend restart. See [`docs/CUSTOM_BUSINESS_DATA.md`](docs/CUSTOM_BUSINESS_DATA.md).

The MVP has no API authentication or tenancy boundary. Snapshot IDs identify process-local data but are not authorization credentials. ARUNA explicitly optimizes supplier-to-factory and warehouse-to-store road legs; the current factory-to-warehouse transfer remains an aggregate planning abstraction.

## What is real and what is synthetic

The FastAPI API, Random Forest inference with `predict_proba`, NetworkX risk-aware routing, OR-Tools CP-SAT optimization, impact propagation, manufacturing/logistics/commerce decisions, and KPI calculations are executable computations. The active road snapshot is derived from OpenStreetMap. The active model is trained on Global Flood Database corridor labels across multiple Indonesian regions. March 2025 flood geometry, facilities, and vehicles remain transparent demo inputs. Business products, prices, orders, inventory, materials, and BOM are either the demo snapshot or an explicitly labeled user upload.

Phase D status: both Jakarta-only scientific attempts remain documented failures. Objective multi-region Indonesia discovery produced a feasible historical corridor-exposure dataset, and the selected model now runs offline over Jakarta as the deployment/demo pilot. Jakarta is not a labeled validation region; unseen-region recall is limited and Jakarta contains two unseen road categories. See [`docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md`](docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md), [`docs/FLOOD_RISK_MODEL_REPORT.md`](docs/FLOOD_RISK_MODEL_REPORT.md), and [`docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md`](docs/GLOBAL_FLOOD_DATABASE_FEASIBILITY.md).

## Manual development

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
