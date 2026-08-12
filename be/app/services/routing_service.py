from __future__ import annotations

from functools import lru_cache

import networkx as nx

from app.core.config import get_settings
from app.repositories.geospatial_repository import get_road_features, get_routing_graph
from app.schemas.disruption import Route

RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@lru_cache(maxsize=1)
def _base_graph() -> nx.DiGraph:
    return _build_graph({})


def warm_graphs() -> None:
    _base_graph()


def _build_graph(road_risks: dict[str, dict]) -> nx.DiGraph:
    settings = get_settings()
    penalties = {
        "low": 0,
        "medium": settings.risk_penalty_medium,
        "high": settings.risk_penalty_high,
        "critical": settings.risk_penalty_critical,
    }
    graph = nx.DiGraph()
    graph_data = get_routing_graph()
    features = {feature["properties"]["segmentId"]: feature for feature in get_road_features().get("features", [])}
    for node in graph_data.get("nodes", []):
        graph.add_node(node["id"], coordinates=node["coordinates"], facility_id=node.get("facilityId"))
    for record in graph_data.get("edges", []):
        feature = features[record["segmentId"]]
        properties = feature["properties"]
        base_time = float(properties["travelTimeMinutes"])
        risk_level = road_risks.get(record["segmentId"], {}).get("riskLevel", "low")
        attributes = {
            "segment_id": record["segmentId"],
            "weight": base_time * (1 + penalties[risk_level]),
            "base_time": base_time,
            "length_km": float(properties["lengthKm"]),
            "geometry": feature["geometry"],
        }
        graph.add_edge(record["fromNode"], record["toNode"], **attributes)
        if record.get("bidirectional"):
            reverse = dict(attributes)
            reverse["geometry"] = {
                "type": feature["geometry"]["type"],
                "coordinates": list(reversed(feature["geometry"]["coordinates"])),
            }
            graph.add_edge(record["toNode"], record["fromNode"], **reverse)
    return graph


def calculate_routes(origin_id: str, destination_id: str, road_risks: dict[str, dict]) -> list[Route]:
    facility_nodes = {
        node.get("facilityId"): node["id"] for node in get_routing_graph().get("nodes", []) if node.get("facilityId")
    }
    start, end = facility_nodes.get(origin_id), facility_nodes.get(destination_id)
    if not start or not end:
        return []
    baseline = _shortest_route(_base_graph(), start, end, "baseline", origin_id, destination_id, road_risks)
    recovery = _shortest_route(_build_graph(road_risks), start, end, "recovery", origin_id, destination_id, road_risks)
    if baseline is None:
        return [recovery] if recovery else []
    if recovery and recovery.affected_road_segment_ids != baseline.affected_road_segment_ids:
        return [baseline, recovery]
    return [baseline]


def _shortest_route(
    graph: nx.DiGraph,
    start: str,
    end: str,
    route_type: str,
    origin_id: str,
    destination_id: str,
    road_risks: dict[str, dict],
) -> Route | None:
    try:
        path = nx.shortest_path(graph, start, end, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    segments: list[str] = []
    coordinates: list[tuple[float, float]] = []
    distance = 0.0
    eta = 0.0
    probability = 0.0
    risk_level = "low"
    for source, target in zip(path, path[1:], strict=False):
        edge = graph[source][target]
        segments.append(edge["segment_id"])
        distance += edge["length_km"]
        eta += edge["base_time"]
        for coordinate in edge["geometry"]["coordinates"]:
            point = tuple(coordinate)
            if not coordinates or coordinates[-1] != point:
                coordinates.append(point)
        risk = road_risks.get(edge["segment_id"], {})
        probability = max(probability, float(risk.get("riskProbability", 0)))
        level = risk.get("riskLevel", "low")
        if RISK_RANK[level] > RISK_RANK[risk_level]:
            risk_level = level
    return Route(
        id=f"route-{route_type}-{origin_id}-{destination_id}",
        type=route_type,
        origin_facility_id=origin_id,
        destination_facility_id=destination_id,
        geometry={"type": "LineString", "coordinates": coordinates},
        distance_km=round(distance, 2),
        eta_minutes=round(eta),
        flood_exposure=risk_level,
        flood_exposure_probability=round(probability, 4),
        affected_road_segment_ids=segments,
    )
