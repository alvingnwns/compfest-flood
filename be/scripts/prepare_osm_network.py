from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, mapping

BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIO_PATH = BASE_DIR / "app" / "data" / "scenarios" / "historical-jakarta-20250304.json"
ROADS_DIR = BASE_DIR / "app" / "data" / "roads"
GRAPH_PATH = ROADS_DIR / "jakarta-2025-03-04-routing-graph.json"
FEATURES_PATH = ROADS_DIR / "jakarta-2025-03-04-road-features.geojson"

BBOX = (106.755, -6.250, 106.940, -6.125)
HIGHWAY_FILTER = (
    '["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|'
    'tertiary|tertiary_link|residential|service"]'
)
SPEEDS_KPH = {
    "motorway": 60,
    "motorway_link": 40,
    "trunk": 50,
    "trunk_link": 35,
    "primary": 40,
    "primary_link": 30,
    "secondary": 35,
    "secondary_link": 25,
    "tertiary": 30,
    "tertiary_link": 20,
    "residential": 20,
    "service": 15,
}


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def _first(value: Any, fallback: str) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    return str(value) if value is not None else fallback


def _facility_pairs(scenario: dict[str, Any]) -> list[tuple[str, str]]:
    by_kind: dict[str, list[str]] = {}
    for facility in scenario["facilities"]:
        by_kind.setdefault(facility["kind"], []).append(facility["id"])
    pairs = [(supplier, factory) for supplier in by_kind["supplier"] for factory in by_kind["factory"]]
    pairs.extend((warehouse, store) for warehouse in by_kind["warehouse"] for store in by_kind["store"])
    return pairs


def _select_corridors(
    graph: nx.MultiDiGraph,
    facility_nodes: dict[str, int],
    facility_pairs: list[tuple[str, str]],
    alternatives: int,
) -> tuple[dict[tuple[int, int], int], list[dict[str, Any]]]:
    selected: dict[tuple[int, int], int] = {}
    paths_metadata: list[dict[str, Any]] = []
    for origin_id, destination_id in facility_pairs:
        origin = facility_nodes[origin_id]
        destination = facility_nodes[destination_id]
        try:
            paths = ox.routing.k_shortest_paths(graph, origin, destination, alternatives, weight="travel_time")
            for rank, path in enumerate(paths, start=1):
                for source, target in zip(path, path[1:], strict=False):
                    candidates = graph.get_edge_data(source, target)
                    key = min(candidates, key=lambda item: float(candidates[item]["travel_time"]))
                    selected[source, target] = key
                paths_metadata.append(
                    {
                        "originFacilityId": origin_id,
                        "destinationFacilityId": destination_id,
                        "alternativeRank": rank,
                        "nodeCount": len(path),
                    }
                )
        except nx.NetworkXNoPath as error:
            raise RuntimeError(f"No OSM route from {origin_id} to {destination_id}") from error
    return selected, paths_metadata


def prepare(*, retrieved_at: str, alternatives: int) -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    ox.settings.use_cache = True
    ox.settings.requests_timeout = 240
    graph = ox.graph_from_bbox(
        BBOX,
        network_type="drive_service",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
        custom_filter=HIGHWAY_FILTER,
    )
    graph = ox.routing.add_edge_speeds(graph, hwy_speeds=SPEEDS_KPH, fallback=20)
    graph = ox.routing.add_edge_travel_times(graph)

    facility_nodes = {
        facility["id"]: int(
            ox.distance.nearest_nodes(
                graph,
                X=facility["location"]["coordinates"][0],
                Y=facility["location"]["coordinates"][1],
            )
        )
        for facility in scenario["facilities"]
    }
    facility_snapping = {}
    for facility in scenario["facilities"]:
        node_id = facility_nodes[facility["id"]]
        source_lon, source_lat = facility["location"]["coordinates"]
        snapped_lon = float(graph.nodes[node_id]["x"])
        snapped_lat = float(graph.nodes[node_id]["y"])
        facility_snapping[facility["id"]] = {
            "nodeId": str(node_id),
            "sourceCoordinates": [source_lon, source_lat],
            "snappedCoordinates": [round(snapped_lon, 7), round(snapped_lat, 7)],
            "distanceMeters": round(
                float(ox.distance.great_circle(source_lat, source_lon, snapped_lat, snapped_lon)), 2
            ),
        }
    selected_edges, selected_paths = _select_corridors(
        graph,
        facility_nodes,
        _facility_pairs(scenario),
        alternatives,
    )
    selected_nodes = {node for edge in selected_edges for node in edge}
    selected_nodes.update(facility_nodes.values())

    nodes = [
        {
            "id": str(node_id),
            "coordinates": [round(float(graph.nodes[node_id]["x"]), 7), round(float(graph.nodes[node_id]["y"]), 7)],
        }
        for node_id in sorted(selected_nodes)
    ]
    categories: Counter[str] = Counter()
    edges = []
    features = []
    for (source, target), key in sorted(selected_edges.items()):
        data = graph[source][target][key]
        segment_id = f"osm-{source}-{target}-{key}"
        highway = _first(data.get("highway"), "unclassified")
        categories[highway] += 1
        geometry = data.get("geometry") or LineString(
            [
                (graph.nodes[source]["x"], graph.nodes[source]["y"]),
                (graph.nodes[target]["x"], graph.nodes[target]["y"]),
            ]
        )
        coordinates = [[round(float(x), 7), round(float(y), 7)] for x, y in mapping(geometry)["coordinates"]]
        osm_ids = _plain(data.get("osmid"))
        if not isinstance(osm_ids, list):
            osm_ids = [osm_ids]
        properties = {
            "segmentId": segment_id,
            "roadName": _first(data.get("name"), "Unnamed OSM road"),
            "lengthKm": round(float(data["length"]) / 1_000, 6),
            "travelTimeMinutes": round(float(data["travel_time"]) / 60, 6),
            "speedKph": round(float(data["speed_kph"]), 2),
            "osmWayIds": [str(item) for item in osm_ids if item is not None],
            "u": str(source),
            "v": str(target),
            "key": int(key),
            "highway": highway,
            "name": _plain(data.get("name")),
            "maxspeed": _plain(data.get("maxspeed")),
            "oneway": bool(data.get("oneway", False)),
            "source": "OpenStreetMap",
        }
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        )
        edges.append({"fromNode": str(source), "toNode": str(target), "segmentId": segment_id})

    metadata = {
        "source": "OpenStreetMap contributors",
        "sourceUrl": "https://www.openstreetmap.org",
        "license": "ODbL 1.0",
        "retrievedAt": retrieved_at,
        "method": "OSMnx 2.1.1 graph_from_bbox via Overpass; four shortest travel-time corridors per facility OD",
        "bbox": {"west": BBOX[0], "south": BBOX[1], "east": BBOX[2], "north": BBOX[3]},
        "highwayFilter": HIGHWAY_FILTER,
        "speedAssumptionsKph": SPEEDS_KPH,
        "fullGraph": {"nodes": graph.number_of_nodes(), "directedEdges": graph.number_of_edges()},
        "processedGraph": {
            "nodes": len(nodes),
            "directedEdges": len(edges),
            "uniqueSegments": len(features),
            "roadCategories": dict(sorted(categories.items())),
        },
        "facilityNodeMappings": {key: str(value) for key, value in sorted(facility_nodes.items())},
        "facilitySnapping": dict(sorted(facility_snapping.items())),
        "selectedPaths": selected_paths,
        "coordinateReferenceSystem": "EPSG:4326",
        "runtimeExternalDependency": None,
    }
    hash_payload = json.dumps(
        {
            "nodes": nodes,
            "edges": edges,
            "features": features,
            "facilityNodeMappings": metadata["facilityNodeMappings"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    metadata["processedContentSha256"] = hashlib.sha256(hash_payload).hexdigest()
    graph_payload = {"metadata": metadata, "nodes": nodes, "edges": edges}
    feature_payload = {"type": "FeatureCollection", "metadata": metadata, "features": features}
    ROADS_DIR.mkdir(parents=True, exist_ok=True)
    GRAPH_PATH.write_text(json.dumps(graph_payload, separators=(",", ":")), encoding="utf-8")
    FEATURES_PATH.write_text(json.dumps(feature_payload, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the compact offline Jakarta OpenStreetMap routing snapshot.")
    parser.add_argument("--retrieved-at", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--alternatives", type=int, default=4)
    args = parser.parse_args()
    if args.alternatives < 2:
        parser.error("--alternatives must be at least 2")
    prepare(retrieved_at=args.retrieved_at, alternatives=args.alternatives)


if __name__ == "__main__":
    main()
