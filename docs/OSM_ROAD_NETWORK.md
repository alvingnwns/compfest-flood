# Jakarta OpenStreetMap Road Network

Status: **C1 complete and active**. Runtime routing now loads a compact OpenStreetMap-derived snapshot rather than the former hand-authored graph.

## Provenance

- Provider: OpenStreetMap contributors
- Source: `https://www.openstreetmap.org`, queried through the public Overpass API with OSMnx 2.1.1
- Retrieval date recorded in snapshot: 2026-08-12
- License: Open Data Commons Open Database License (ODbL) 1.0; attribution: © OpenStreetMap contributors
- Pilot bounding box, EPSG:4326: west 106.755, south -6.250, east 106.940, north -6.125
- Processed-content SHA-256: stored in each artifact's `metadata.processedContentSha256`

The filter includes `motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `residential`, `service`, and their relevant `_link` categories. Other highway categories are excluded to keep the graph relevant to urban vehicle logistics.

## Preparation and artifacts

Preparation is offline-only and reproducible:

```powershell
cd be
python -m pip install -e ".[data]"
python scripts/prepare_osm_network.py --retrieved-at YYYY-MM-DD --alternatives 4
```

The query returned 64,053 nodes and 145,385 directed edges. Four shortest travel-time alternatives were evaluated for each supplier→factory and warehouse→store pair. Their union produces the compact runtime snapshot:

- 1,383 nodes
- 1,413 directed/unique processed segments
- 26 motorway, 20 motorway_link, 792 primary, 19 primary_link, 126 secondary, 2 secondary_link, 95 tertiary, 247 trunk, 13 trunk_link, 53 residential, and 20 service segments
- Routing graph: `be/app/data/roads/jakarta-2025-03-04-routing-graph.json` (about 216 KB)
- GeoJSON: `be/app/data/roads/jakarta-2025-03-04-road-features.geojson` (about 716 KB)

Every segment has a stable processed ID `osm-{u}-{v}-{key}` and retains `osmWayIds`, `u`, `v`, `key`, `highway`, `name`, `maxspeed`, and `oneway` where available. GeoJSON coordinates remain `[longitude, latitude]`.

## Facility snapping

The ten simulated business facilities retain geographically valid Jakarta coordinates and are snapped with OSMnx nearest-node lookup. The node mapping and source/snapped coordinates are persisted. Snap distances range from 5.18 m to 85.48 m; all are below 100 m. Runtime never hardcodes the old synthetic node IDs.

## Travel time and route cost

OSMnx calculates edge length from geometry. Speed comes from OSM `maxspeed` where usable, otherwise a documented category default: motorway 60, trunk 50, primary 40, secondary 35, tertiary 30, residential 20, service 15 km/h, with lower link-road defaults. These are free-flow planning assumptions, not measured Jakarta traffic.

Baseline route cost is:

`sum(edge.travelTimeMinutes)`

Risk-aware edge weight remains centralized in backend settings:

`travelTimeMinutes × (1 + riskPenalty[riskLevel])`

Current default penalties are low 0, medium 2, high 5, and critical 15. NetworkX computes both paths from the same local snapshot.

## Limitations

- This is a compact union of business-relevant alternative corridors, not every Jakarta road at runtime.
- OSM is continuously edited; the committed snapshot represents the recorded retrieval.
- Speeds are static assumptions and exclude congestion, incidents, turn penalties, and live closures.
- The active model is the historical multi-region Indonesia corridor-exposure model. Jakarta remains an unvalidated, partially out-of-distribution deployment/demo pilot; the two earlier Jakarta-only feasibility failures remain documented separately.
