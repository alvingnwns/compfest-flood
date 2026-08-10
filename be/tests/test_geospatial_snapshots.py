from app.repositories.geospatial_repository import (
    get_historical_flood_extent,
    get_road_features,
    get_routing_graph,
)


def test_local_flood_snapshot_is_geojson_polygon() -> None:
    flood_extent = get_historical_flood_extent()

    assert flood_extent["type"] == "FeatureCollection"
    assert flood_extent["features"][0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert flood_extent["features"][0]["properties"]["sourceMode"] == "synthetic_historical_replay"


def test_routing_graph_references_existing_road_features() -> None:
    road_features = get_road_features()
    routing_graph = get_routing_graph()
    segment_ids = {feature["properties"]["segmentId"] for feature in road_features["features"]}
    node_ids = {node["id"] for node in routing_graph["nodes"]}

    assert len(segment_ids) >= 2
    assert all(edge["segmentId"] in segment_ids for edge in routing_graph["edges"])
    assert all(edge["fromNode"] in node_ids and edge["toNode"] in node_ids for edge in routing_graph["edges"])


def test_road_features_have_future_risk_model_inputs() -> None:
    road_feature = get_road_features()["features"][0]
    properties = road_feature["properties"]

    assert road_feature["geometry"]["type"] == "LineString"
    assert {"rainfallMm", "hazardScore", "elevationMeters", "historicalFloodExposure", "drainagePressure"} <= properties.keys()
