from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import ee
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping, shape

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data" / "indonesia-flood-ml"
DISCOVERY_PATH = DATA_DIR / "region-discovery.json"
BOUNDARIES_PATH = DATA_DIR / "selected-region-boundaries.geojson"
ROADS_DIR = DATA_DIR / "roads"
SUMMARY_PATH = DATA_DIR / "road-preparation-summary.json"
ADMIN_COLLECTION_ID = "FAO/GAUL/2015/level2"
HIGHWAY_FILTER = (
    '["highway"~"motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|'
    'tertiary|tertiary_link"]'
)
OVERPASS_ENDPOINTS = (
    "https://lz4.overpass-api.de/api",
    "https://z.overpass-api.de/api",
    "https://overpass-api.de/api",
)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _first(value: Any, fallback: str) -> str:
    values = _as_list(value)
    return values[0] if values else fallback


def _boundaries(project: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    ee.Initialize(project=project)
    codes = [item["gaulAdmin2Code"] for item in selected]
    regions = ee.FeatureCollection(ADMIN_COLLECTION_ID).filter(ee.Filter.inList("ADM2_CODE", codes))

    def normalize(feature: ee.Feature) -> ee.Feature:
        feature = ee.Feature(feature)
        return ee.Feature(
            feature.geometry().simplify(maxError=100),
            {
                "regionId": ee.String("gaul2-").cat(ee.Number(feature.get("ADM2_CODE")).format("%.0f")),
                "gaulAdmin1Code": feature.get("ADM1_CODE"),
                "gaulAdmin2Code": feature.get("ADM2_CODE"),
                "province": feature.get("ADM1_NAME"),
                "region": feature.get("ADM2_NAME"),
            },
        )

    payload = regions.map(normalize).getInfo()
    payload["metadata"] = {
        "source": ADMIN_COLLECTION_ID,
        "country": "Indonesia",
        "simplificationToleranceMeters": 100,
        "purpose": "Reproducible OSM query boundaries; not a predictive feature.",
    }
    BOUNDARIES_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return payload


def _process_graph(graph: nx.MultiDiGraph, region: dict[str, Any]) -> dict[str, Any]:
    records = []
    categories: Counter[str] = Counter()
    for u, v, key, data in graph.edges(keys=True, data=True):
        geometry = data.get("geometry") or LineString(
            [(graph.nodes[u]["x"], graph.nodes[u]["y"]), (graph.nodes[v]["x"], graph.nodes[v]["y"])]
        )
        if geometry.geom_type != "LineString":
            continue
        highway = _first(data.get("highway"), "unclassified")
        segment_id = f"osm-{region['regionId']}-{u}-{v}-{key}"
        properties = {
            "segmentId": segment_id,
            "regionId": region["regionId"],
            "province": region["province"],
            "region": region["region"],
            "roadName": _first(data.get("name"), "Unnamed OSM road"),
            "highway": highway,
            "lengthMeters": round(float(data.get("length", geometry.length)), 3),
            "osmWayIds": sorted(set(_as_list(data.get("osmid")))),
            "u": str(u),
            "v": str(v),
            "key": int(key),
            "oneway": bool(data.get("oneway", False)),
            "source": "OpenStreetMap",
        }
        records.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry),
            }
        )
        categories[highway] += 1
    records.sort(key=lambda feature: feature["properties"]["segmentId"])
    metadata = {
        "source": "OpenStreetMap contributors",
        "sourceUrl": "https://www.openstreetmap.org",
        "license": "ODbL 1.0",
        "retrievedAt": datetime.now(UTC).date().isoformat(),
        "method": "OSMnx graph_from_polygon; full selected GAUL level-2 polygon; logistics road filter",
        "highwayFilter": HIGHWAY_FILTER,
        "networkType": "drive",
        "simplifyGraph": True,
        "retainAllComponents": True,
        "regionId": region["regionId"],
        "province": region["province"],
        "region": region["region"],
        "graphNodes": graph.number_of_nodes(),
        "directedSegments": len(records),
        "roadCategories": dict(sorted(categories.items())),
        "runtimeExternalDependency": None,
    }
    payload = {"type": "FeatureCollection", "metadata": metadata, "features": records}
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    payload["metadata"]["processedContentSha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def _download_graph(polygon: Any, region_id: str) -> tuple[nx.MultiDiGraph, str]:
    failures = []
    for endpoint in OVERPASS_ENDPOINTS:
        ox.settings.overpass_url = endpoint
        try:
            graph = ox.graph_from_polygon(
                polygon,
                network_type="drive",
                simplify=True,
                retain_all=True,
                truncate_by_edge=True,
                custom_filter=HIGHWAY_FILTER,
            )
            return graph, endpoint
        except Exception as error:  # noqa: BLE001 - failover must retain endpoint errors
            failure = {
                "endpoint": endpoint,
                "errorType": type(error).__name__,
                "message": str(error)[:500],
            }
            failures.append(failure)
            print(json.dumps({"regionId": region_id, "overpassAttemptFailed": failure}), flush=True)
    raise RuntimeError(f"All Overpass endpoints failed for {region_id}: {json.dumps(failures)}")


def _polygonal_geometry(geometry: Any) -> Polygon | MultiPolygon:
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    polygon_parts = [part for part in getattr(geometry, "geoms", []) if isinstance(part, Polygon)]
    if not polygon_parts:
        raise TypeError(f"Boundary has no polygonal component: {geometry.geom_type}")
    if len(polygon_parts) == 1:
        return polygon_parts[0]
    return MultiPolygon(polygon_parts)


def prepare(project: str, selected_region_ids: set[str] | None = None) -> dict[str, Any]:
    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))
    selected = discovery["selected"]
    unique = {
        row["regionId"]: {
            "regionId": row["regionId"],
            "gaulAdmin2Code": row["gaulAdmin2Code"],
            "province": row["province"],
            "region": row["region"],
        }
        for row in selected
    }
    if selected_region_ids:
        missing = selected_region_ids - unique.keys()
        if missing:
            raise ValueError(f"Unknown selected region IDs: {sorted(missing)}")
        unique = {region_id: region for region_id, region in unique.items() if region_id in selected_region_ids}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ROADS_DIR.mkdir(parents=True, exist_ok=True)
    if BOUNDARIES_PATH.exists():
        boundaries = json.loads(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    else:
        boundaries = _boundaries(project, list({row["regionId"]: row for row in selected}.values()))
    boundary_by_id = {feature["properties"]["regionId"]: feature for feature in boundaries["features"]}
    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.requests_timeout = 120
    ox.settings.http_user_agent = "ARUNA-AIC-2026 historical-flood-road research"
    ox.settings.http_referer = "https://github.com/"
    ox.settings.overpass_rate_limit = True
    summaries = []
    for region_id, region in sorted(unique.items()):
        output_path = ROADS_DIR / f"{region_id}.geojson"
        if output_path.exists():
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        else:
            boundary = boundary_by_id[region_id]
            polygon = _polygonal_geometry(shape(boundary["geometry"]))
            graph, overpass_endpoint = _download_graph(polygon, region_id)
            payload = _process_graph(graph, region)
            payload["metadata"]["overpassEndpoint"] = overpass_endpoint
            output_path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
        summaries.append(
            {
                **region,
                "roadSegments": payload["metadata"]["directedSegments"],
                "graphNodes": payload["metadata"]["graphNodes"],
                "roadCategories": payload["metadata"]["roadCategories"],
                "artifact": output_path.relative_to(BASE_DIR).as_posix(),
                "artifactBytes": output_path.stat().st_size,
                "processedContentSha256": payload["metadata"]["processedContentSha256"],
            }
        )
        print(json.dumps(summaries[-1]), flush=True)
    existing = {}
    if SUMMARY_PATH.exists():
        existing = {
            item["regionId"]: item for item in json.loads(SUMMARY_PATH.read_text(encoding="utf-8")).get("regions", [])
        }
    for item in summaries:
        existing[item["regionId"]] = item
    all_summaries = [existing[key] for key in sorted(existing)]
    result = {
        "metadata": {
            "source": "OpenStreetMap contributors",
            "boundarySource": ADMIN_COLLECTION_ID,
            "highwayFilter": HIGHWAY_FILTER,
            "selectionIndependentOfRoadLabels": True,
        },
        "summary": {
            "regionsPrepared": len(all_summaries),
            "roadSegments": sum(item["roadSegments"] for item in all_summaries),
            "geometryBytes": sum(item["artifactBytes"] for item in all_summaries),
        },
        "regions": all_summaries,
    }
    SUMMARY_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare real OSM logistics roads for selected Indonesia regions.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--region-id", action="append", default=[])
    args = parser.parse_args()
    result = prepare(args.project, set(args.region_id) or None)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
