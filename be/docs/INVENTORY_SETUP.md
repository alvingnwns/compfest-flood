# Inventory backend setup and handoff

## Environment

The backend reads `be/.env` first and uses the repository `.env` as a fallback. Keep secrets out of Git.

```env
INVENTORY_DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres?sslmode=require
OPENROUTER_API_KEY=...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_QWEN_MODEL=qwen/qwen3.5-flash-02-23
INVENTORY_PROCUREMENT_BUDGET_IDR=1000000
INVENTORY_SOLVER_TIMEOUT_SECONDS=5
```

Use the Supabase session pooler for local IPv4 environments. `INVENTORY_MODEL_DIR` is optional and defaults to `be/artifacts/inventory`.

## Install, migrate, seed, train

```powershell
cd be
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scripts/migrate_inventory.py
python scripts/seed_inventory.py
python scripts/train_inventory_demand.py --dataset data/new_data/aruna_juice.csv --output artifacts/inventory
```

Migration creates the isolated PostgreSQL schema `aruna_inventory`. The earlier public draft tables are not modified. The seed is idempotent before sales exist and is documented in `INVENTORY_DEMO_ASSUMPTIONS.md`.

## Run

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Docker image includes the inventory model artifacts. The root Compose file is outside this backend-only scope and does not currently pass `INVENTORY_DATABASE_URL`; inject it explicitly when running the backend container.

## Frontend endpoint mapping

| Page | Endpoint |
| --- | --- |
| POS catalog | `GET /api/products` |
| POS checkout | `POST /api/transactions` |
| Sales | `GET /api/transactions`, `GET /api/transactions/{id}` |
| Warehouse | `GET /api/inventory`, `GET /api/inventory/movements` |
| Stock count | `POST /api/inventory/{ingredientId}/adjustments` |
| Receiving | `POST /api/inventory/{ingredientId}/stock-in` |
| Demand | `GET /api/forecasts/products/{productId}?horizonDays=3` |
| Risk | `GET /api/inventory/risks` |
| Procurement | `GET /api/procurement/recommendations` |
| Owner decision | `POST /api/procurement/recommendations/{recommendationId}/decision` |
| Dashboard | `GET /api/dashboard/summary` |

All JSON uses camelCase. New inventory errors use `{ "error": { "code", "message", "details" } }`. POS checkout, stock adjustment, and stock-in accept optional `Idempotency-Key`. After mutations, invalidate the FE queries listed in `INVENTORY_BACKEND_CONTRACT.md`.

## Verification commands

```powershell
$env:TMP="$PWD\.test-tmp"
$env:TEMP=$env:TMP
python -m pytest tests/test_inventory_product_track.py
python scripts/verify_inventory_concurrency.py
python -m pytest
```

The concurrency verifier creates two competing checkouts, expects exactly one to commit, then reverses the successful transaction and checks that stock returns to its original balance.

## Operational boundaries

- Approval records owner intent only. It does not contact a supplier, spend money, or increase stock.
- Stock changes on physical receiving or stocktaking only.
- Approved outstanding quantities reserve optimizer budget but are not counted as confirmed inbound inventory.
- Qwen explains persisted risk and OR-Tools decisions. Provider/schema failure uses deterministic fallback without changing recommendations.
- Activity logs and inventory movements are separate. Activity partitions use WIB month boundaries; event timestamps remain UTC.
- Product Track results are not preliminary recovery evaluation improvements.
