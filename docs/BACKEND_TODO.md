# ResiliChain AI Backend Status

The stabilization phase connects the existing real algorithms without claiming real-world data validity. The source of truth for HTTP behavior remains [`BACKEND_INTEGRATION_CONTRACT.md`](./BACKEND_INTEGRATION_CONTRACT.md).

## Completed in stabilization

- [x] One authoritative `be/pyproject.toml` dependency source and matching Docker install.
- [x] FastAPI application factory, environment-driven CORS, startup model/graph warmup, and structured errors.
- [x] Seven frontend endpoints and synchronous contract-compatible lifecycle.
- [x] Process-local fingerprint idempotency for simulation and recovery POST requests.
- [x] Real `predict_proba` inference from a cached Logistic Regression artifact.
- [x] Real NetworkX baseline and flood-risk-aware routes on the local graph.
- [x] Generic road → route → facility → material/inventory → product → order impact propagation.
- [x] CP-SAT production, fulfillment, substitution, warehouse, vehicle, route, deadline, and delay decisions.
- [x] Frontend-compatible `partial` and reachable `no-feasible-plan` responses.
- [x] All five KPIs derived from optimizer outcomes.
- [x] Tests for contract flow, referential integrity, routing/probability, business consistency, sensitivity, idempotency, and infeasibility.
- [x] Removed the unused parallel fixture/stub architecture after import tracing.

## Current truth

| Component | Algorithm/runtime | Input data |
| --- | --- | --- |
| Flood risk | Real Logistic Regression inference | Synthetic features and labels |
| Routing | Real NetworkX shortest path | Synthetic road graph |
| Recovery | Real OR-Tools CP-SAT solve | Synthetic business scenario |
| Impact and KPIs | Real data-driven computation | Derived from the synthetic replay |

Risk probabilities are not flood-certainty claims, and evaluation metrics do not establish scientific validity on real floods.

## Deliberately deferred

- [ ] Real historical labels and validated flood-event snapshots.
- [ ] Sentinel-1/Earth Engine and rainfall/hazard ingestion.
- [ ] OSM/OSMnx road-network ingestion and validation.
- [ ] Persistent database and durable idempotency.
- [ ] Authentication/authorization.
- [ ] Distributed/background job execution.
- [ ] Full multi-stop vehicle-routing optimization.

The next phase is **real historical/remote-sensing data plus a real OSM road network**. It must validate provenance and scientific claims before the synthetic labels or graph are replaced.
