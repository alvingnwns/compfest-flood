# ResiliChain AI Backend

FastAPI backend for an offline-first synthetic Jakarta flood replay. The HTTP contract is frozen in [`../docs/BACKEND_INTEGRATION_CONTRACT.md`](../docs/BACKEND_INTEGRATION_CONTRACT.md).

The computation pipeline is connected: Logistic Regression probabilities affect NetworkX route costs and supplier availability; those results feed OR-Tools production, inventory, warehouse, vehicle, substitution, and order-allocation decisions; recovery outputs drive all five KPIs. The runtime road graph is derived from OpenStreetMap; ML training labels, the flood snapshot, and company scenario remain synthetic.

## Setup

Python 3.11 or newer is supported. `pyproject.toml` is the authoritative dependency manifest; `requirements.txt` is a compatibility list with matching ranges.

```powershell
cd be
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Check `http://localhost:8000/health`. Docker uses the same `pyproject.toml` source:

```powershell
docker build -t resilichain-backend .
docker run --rm -p 8000:8000 resilichain-backend
```

## Active computation

- Flood inference: cached Joblib Logistic Regression artifact and raw `predict_proba` values.
- Routing: cached compact OpenStreetMap-derived NetworkX graph; baseline minimizes estimated travel time and recovery adds configurable risk penalties.
- Supplier availability: route risk reduces each supplier material's expected quantity using the documented policy in `Settings`.
- Recovery: CP-SAT integer quantities enforce BOM/material supply, factory capacity, inventory, explicit substitution, warehouse and vehicle assignment, vehicle capacity/availability, route feasibility, order demand, deadlines, and optional maximum additional delay.
- Objective: maximize priority-weighted fulfillment while penalizing unfulfilled quantity, delay, transport cost, substitution, and route risk. Weights live in `app/core/config.py`.
- Lifecycle: synchronous and honest. A completed response is returned after computation; schema states remain compatible with future asynchronous execution.
- Idempotency: identical simulation and recovery requests reuse process-local artifacts. This resets on process restart because the MVP has no persistent store.

## KPI formulas

- Orders Fulfilled = count of orders whose allocated quantity equals requested quantity (the response also supplies the total-order denominator).
- On-Time Delivery = fully fulfilled orders arriving within their deadline / total orders.
- Failed Orders = orders with zero allocated quantity.
- Average Delay = mean `max(0, route ETA - deadline)` across delivered orders, in minutes.
- Sales Exposure Risk = sum of `unfulfilled quantity × product unitPrice`, in raw IDR.

## Scope and limitations

Vehicle capacity is modeled as aggregate planning capacity per vehicle, not a full vehicle-routing problem. State is process-local. There is no authentication, database, queue, or runtime external data ingestion. Do not describe this version as historical flood AI: the road geometry is OSM-derived and algorithms execute for real, but the runtime flood model and business inputs remain synthetic. Earth Engine processing produced no defensible positive road labels, so the Phase C scientific feasibility gate failed and historical training was prohibited.
