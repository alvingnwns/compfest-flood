# ARUNA Backend

FastAPI backend for ARUNA's offline-capable flood-exposure and supply-chain recovery decision-support MVP. The HTTP boundary is documented in [the integration contract](../docs/BACKEND_INTEGRATION_CONTRACT.md).

The backend also contains the PostgreSQL-backed Inventory Product Track for POS,
three-day juice demand forecasting, inventory risk, procurement recommendations,
and the owner dashboard. Its frontend contract and setup are documented in
[`docs/INVENTORY_BACKEND_CONTRACT.md`](docs/INVENTORY_BACKEND_CONTRACT.md) and
[`docs/INVENTORY_SETUP.md`](docs/INVENTORY_SETUP.md).

## Setup

Python 3.11 or newer is supported. pyproject.toml is authoritative.

~~~powershell
cd be
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
uvicorn app.main:app --host 0.0.0.0 --port 8000
~~~

Docker installs from the same manifest. The supported engine setting is ENGINE_MODE=connected.

## Inventory Product Track

```powershell
python scripts/migrate_inventory.py
python scripts/seed_inventory.py
python scripts/train_inventory_demand.py --dataset data/new_data/aruna_juice.csv --output artifacts/inventory
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set `INVENTORY_DATABASE_URL` to the Supabase PostgreSQL session-pooler URL. The
inventory domain uses the isolated `aruna_inventory` schema. Quantity changes are
ledger backed, operational timestamps are UTC, and business dates and monthly
activity partitions use Asia/Jakarta.

## Active computation

- Historical Replay loads the committed, SHA-256-verified Joblib Random Forest trained from historical Global Flood Database road-corridor labels across Indonesian regions.
- Dynamic Hazard is a historical-derived Q1-Q4 what-if transformation. It is not live weather or a calibrated future flood forecast.
- Routing loads a compact local OpenStreetMap-derived graph. NetworkX computes normal travel-time baselines and risk-aware candidates.
- A candidate route is not a selected recovery route. Selection is established only by a successful ready or partial optimizer result that references it; no-feasible-plan selects none.
- OR-Tools CP-SAT coordinates manufacturing quantities, material/BOM feasibility, inventory, warehouse allocation, downstream vehicle/route assignment, substitution, deadlines, and order fulfillment.
- Custom Business Data replaces products, prices, orders, inventory, materials, and BOM while retaining the demo Jakarta network.
- Impact KPIs are computed from baseline and optimizer outcomes. ARUNA Copilot explains only this grounded evidence through Gemini, then Qwen, then a deterministic local fallback.

## KPI formulas

- Orders Fulfilled: fully allocated orders / total orders.
- On-Time Delivery: fully fulfilled on-time orders / total orders.
- Failed Orders: orders with zero allocated quantity.
- Average Delay: mean max(0, ETA - deadline) across delivered orders. The API also exposes observation counts so clients can show N/A when none were delivered.
- Sales Exposure Risk: sum of unfulfilled quantity × unit price in raw IDR.

## Modeling and MVP boundaries

ARUNA coordinates production, warehouse allocation, downstream distribution, and order fulfillment. Supplier-to-factory and warehouse-to-store road legs are explicitly routed; the current MVP abstracts factory-to-warehouse transfer and does not claim that every physical transport leg is road/vehicle optimized. Vehicle capacity is aggregate planning capacity, not a vehicle-routing problem.

Simulation, recovery, custom snapshots, and Copilot backend context remain
process-local. The Inventory Product Track is persisted in PostgreSQL, but neither
track currently provides API authentication, tenancy, a queue, live weather
ingestion, or operational purchasing authority. Snapshot IDs are identifiers,
not authorization. The March 2025 geometry and business network are transparent
demo inputs, and Jakarta is a deployment/demo pilot rather than a labeled
validation region.
