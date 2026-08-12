# Local MVP data

This directory will contain versioned, offline historical-replay snapshots:

- `scenarios/` for business-network snapshots;
- `floods/` for historical flood GeoJSON;
- `roads/` for road features and local routing graphs; and
- `datasets/` for reproducible flood-risk training data.

No external API is required to run the MVP demo.

The initial `jakarta-2025-03-04-*` runtime scenario assets remain synthetic and intentionally marked as such. Separately, `flood-events/` contains the failed Sentinel-1 feasibility evidence, while `global-flood-db/` and `datasets/global_flood_road_corridor_labels.csv` contain the failed Global Flood Database fallback evidence. Neither real-data dataset is used by the runtime model.
