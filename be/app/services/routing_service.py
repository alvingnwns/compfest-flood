import networkx as nx

from app.repositories.geospatial_repository import get_road_features, get_routing_graph
from app.schemas.disruption import RouteAnalysis


def build_graph(road_risks_map: dict[str, dict] | None = None) -> nx.DiGraph:
    """
    Builds the NetworkX DiGraph.
    If road_risks_map is provided, adds risk penalty to travelTimeMinutes for weight.
    """
    if road_risks_map is None:
        road_risks_map = {}

    G = nx.DiGraph()
    graph_data = get_routing_graph()
    features_data = get_road_features()

    for node in graph_data.get("nodes", []):
        G.add_node(node["id"], coordinates=node["coordinates"], facilityId=node.get("facilityId"))

    features_map = {}
    for feature in features_data.get("features", []):
        props = feature.get("properties", {})
        features_map[props["segmentId"]] = {
            "travelTimeMinutes": props.get("travelTimeMinutes", 1.0),
            "lengthKm": props.get("lengthKm", 1.0),
            "geometry": feature.get("geometry"),
        }

    for edge in graph_data.get("edges", []):
        u = edge["fromNode"]
        v = edge["toNode"]
        segment_id = edge["segmentId"]

        feature = features_map.get(segment_id, {})
        base_time = feature.get("travelTimeMinutes", 1.0)
        dist = feature.get("lengthKm", 1.0)
        geom = feature.get("geometry")

        weight = base_time
        risk_info = road_risks_map.get(segment_id)
        if risk_info:
            level = risk_info.get("riskLevel", "low")
            if level == "critical":
                weight += base_time * 10
            elif level == "high":
                weight += base_time * 5
            elif level == "medium":
                weight += base_time * 2

        G.add_edge(
            u, v, segmentId=segment_id, weight=weight, base_time=base_time, lengthKm=dist, geometry=geom
        )
        if edge.get("bidirectional"):
            # A strict geometrical approach would reverse the LineString, 
            # but MultiLineString rendering handles exact segment duplicates cleanly.
            G.add_edge(
                v, u, segmentId=segment_id, weight=weight, base_time=base_time, lengthKm=dist, geometry=geom
            )

    return G


def calculate_routes(
    origin_facility_id: str, dest_facility_id: str, road_risks_map: dict[str, dict]
) -> list[RouteAnalysis]:
    graph_data = get_routing_graph()
    fac_to_node = {
        n.get("facilityId"): n["id"] for n in graph_data.get("nodes", []) if n.get("facilityId")
    }

    start_node = fac_to_node.get(origin_facility_id)
    end_node = fac_to_node.get(dest_facility_id)

    if not start_node or not end_node:
        return []

    # Baseline (no penalties)
    g_base = build_graph()
    try:
        path_base = nx.shortest_path(g_base, source=start_node, target=end_node, weight="weight")
        baseline_route = _build_route_analysis(
            g_base, path_base, "baseline", origin_facility_id, dest_facility_id, road_risks_map
        )
    except nx.NetworkXNoPath:
        baseline_route = None

    # Risk-Aware Recovery (with penalties)
    g_risk = build_graph(road_risks_map)
    try:
        path_risk = nx.shortest_path(g_risk, source=start_node, target=end_node, weight="weight")
        recovery_route = _build_route_analysis(
            g_risk, path_risk, "recovery", origin_facility_id, dest_facility_id, road_risks_map
        )
    except nx.NetworkXNoPath:
        recovery_route = None

    routes = []
    if baseline_route:
        routes.append(baseline_route)
        if (
            recovery_route
            and baseline_route.affected_road_segment_ids != recovery_route.affected_road_segment_ids
        ):
            routes.append(recovery_route)
    elif recovery_route:
        routes.append(recovery_route)

    return routes


def _build_route_analysis(
    g: nx.DiGraph,
    path: list[str],
    route_type: str,
    origin: str,
    dest: str,
    road_risks_map: dict[str, dict],
) -> RouteAnalysis:
    segments = []
    dist = 0.0
    eta = 0.0
    max_prob = 0.0
    max_level = "low"
    coords = []

    level_val = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        edge = g[u][v]

        seg_id = edge["segmentId"]
        segments.append(seg_id)
        dist += edge["lengthKm"]
        eta += edge["base_time"]

        geom = edge["geometry"]
        if geom and "coordinates" in geom:
            for pt in geom["coordinates"]:
                if not coords or coords[-1] != pt:
                    coords.append(pt)

        risk = road_risks_map.get(seg_id)
        if risk:
            prob = risk.get("riskProbability", 0.0)
            lvl = risk.get("riskLevel", "low")
            if prob > max_prob:
                max_prob = prob
            if level_val[lvl] > level_val[max_level]:
                max_level = lvl

    geom_obj = {"type": "LineString", "coordinates": coords}

    return RouteAnalysis(
        id=f"route-{route_type}-{origin}-{dest}",
        type=route_type,
        origin_facility_id=origin,
        destination_facility_id=dest,
        geometry=geom_obj,
        distance_km=round(dist, 2),
        eta_minutes=int(eta),
        flood_exposure=max_level,
        flood_exposure_probability=round(max_prob, 2),
        affected_road_segment_ids=segments,
    )
