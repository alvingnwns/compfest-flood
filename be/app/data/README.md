# ARUNA local runtime and research data

ARUNA runs its protected core from versioned local assets:

- roads/: compact OpenStreetMap-derived Jakarta graph and road context;
- indonesia-flood-ml/ and datasets/: historical Global Flood Database discovery, road-corridor labels, features, splits, and reports;
- models/: the active historical Random Forest artifact and metadata, verified by committed SHA-256 before deserialization;
- dynamic-hazard/: historical-derived temporal/representative inputs for Q1-Q4 what-if analysis;
- scenarios/ and floods/: transparent Jakarta demo business and March 2025 replay geometry;
- flood-events/ and related feasibility evidence: retained research/audit artifacts, not alternate runtime fallbacks.

No external API is required for Historical Replay, Dynamic Hazard, OSM/NetworkX routing, CP-SAT recovery, or KPI computation. The historical model uses real historical corridor-exposure labels; the March 2025 pilot geometry and built-in company inputs remain demo data. See the [historical dataset report](../../../docs/INDONESIA_HISTORICAL_FLOOD_DATASET.md) and [model report](../../../docs/FLOOD_RISK_MODEL_REPORT.md).
