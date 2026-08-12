# Local MVP data

This directory will contain versioned, offline historical-replay snapshots:

- `scenarios/` for business-network snapshots;
- `floods/` for historical flood GeoJSON;
- `roads/` for road features and local routing graphs; and
- `datasets/` for reproducible flood-risk training data.

No external API is required to run the MVP demo.

The initial `jakarta-2025-03-04-*` runtime scenario assets remain synthetic and intentionally marked as such. Separately, `flood-events/` and `datasets/historical_road_flood_labels.csv` contain verified event provenance and Earth Engine-derived road-event observations. Those observations failed the scientific feasibility gate and are not used by the runtime model.
