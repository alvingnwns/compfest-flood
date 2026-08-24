"""
Prepare a lightweight surrounding OSM road context dataset for display use.

This is a ONE-TIME preparation step. The output is committed to the repository
and served at runtime — no internet required at runtime.

The resulting dataset is:
  - display-only (NOT inserted into the NetworkX optimization graph)
  - separate from the 1,413-segment analyzed network
  - real OSM road data for the Jakarta pilot area
  - simplified geometry for performance

Usage:
    python scripts/prepare_road_context.py

Output:
    app/data/roads/jakarta-road-context.geojson
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import osmnx as ox
from shapely.geometry import mapping

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "app" / "data" / "roads" / "jakarta-road-context.geojson"

# Same bounding box as the analyzed network — ensures context covers the pilot area
BBOX = (106.755, -6.250, 106.940, -6.125)  # (west, south, east, north)

# Broader road filter than analyzed graph to show more context.
# Excludes service roads, footpaths, tracks for display quality.
HIGHWAY_FILTER = (
    '["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link'
    '|secondary|secondary_link|tertiary|tertiary_link|residential"]'
)

# Coordinate precision for display (6 decimals ≈ 0.1m, sufficient for display)
DISPLAY_PRECISION = 6


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def _first(value: Any, fallback: str) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    return str(value) if value is not None else fallback


def prepare() -> None:
    print(f"Downloading OSM road context for bbox {BBOX}…")
    ox.settings.use_cache = True
    ox.settings.requests_timeout = 300

    # Download undirected graph (bidirectional roads — for display, direction doesn't matter)
    graph = ox.graph_from_bbox(
        BBOX,
        network_type="drive",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
        custom_filter=HIGHWAY_FILTER,
    )

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    print(f"Downloaded graph: {node_count} nodes, {edge_count} directed edges")

    # Convert to undirected to deduplicate reverse edges for display
    undirected = ox.convert.to_undirected(graph)

    features: list[dict[str, Any]] = []
    highway_counts: dict[str, int] = {}

    for u, v, data in undirected.edges(data=True):
        highway = _first(data.get("highway"), "unclassified")
        highway_counts[highway] = highway_counts.get(highway, 0) + 1

        # Build geometry
        geom = data.get("geometry")
        if geom is not None:
            raw_coords = list(mapping(geom)["coordinates"])
        else:
            raw_coords = [
                (float(undirected.nodes[u]["x"]), float(undirected.nodes[u]["y"])),
                (float(undirected.nodes[v]["x"]), float(undirected.nodes[v]["y"])),
            ]

        # Round coordinates for display
        coordinates = [[round(float(x), DISPLAY_PRECISION), round(float(y), DISPLAY_PRECISION)] for x, y in raw_coords]

        osm_ids = _plain(data.get("osmid"))
        if not isinstance(osm_ids, list):
            osm_ids = [osm_ids] if osm_ids is not None else []

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "highway": highway,
                    "name": _first(data.get("name"), ""),
                    "osmWayIds": [str(item) for item in osm_ids],
                    "source": "OpenStreetMap",
                },
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        )

    feature_count = len(features)
    print(f"Built {feature_count} display features across {len(highway_counts)} road classes")
    print(f"Road class breakdown: {dict(sorted(highway_counts.items()))}")

    metadata = {
        "description": "Surrounding OSM road network for display context — NOT the ARUNA optimization graph",
        "purpose": (
            "display-only context layer; optimization graph remains"
            " app/data/roads/jakarta-2025-03-04-routing-graph.json"
        ),
        "source": "OpenStreetMap contributors",
        "sourceUrl": "https://www.openstreetmap.org",
        "license": "ODbL 1.0",
        "retrievedAt": datetime.now(UTC).date().isoformat(),
        "bbox": {"west": BBOX[0], "south": BBOX[1], "east": BBOX[2], "north": BBOX[3]},
        "highwayFilter": HIGHWAY_FILTER,
        "fullGraph": {"nodes": node_count, "directedEdges": edge_count},
        "displayFeatures": feature_count,
        "roadCategories": dict(sorted(highway_counts.items())),
        "coordinateReferenceSystem": "EPSG:4326",
        "runtimeExternalDependency": None,
    }

    payload = {"type": "FeatureCollection", "metadata": metadata, "features": features}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUTPUT_PATH.name} — {feature_count} features, {size_kb:.0f} KB")
    print("This file is display-only. The optimization graph is unchanged.")


if __name__ == "__main__":
    prepare()
