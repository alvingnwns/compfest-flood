import json
from pathlib import Path

from app.repositories.geospatial_repository import get_historical_flood_extent, get_road_features, get_routing_graph
from app.repositories.scenario_repository import get_historical_jakarta
from app.services.flood_risk_service import predict_risk
from app.services.routing_service import _build_graph
from scripts.osm_directionality import routing_edge_record


def test_synthetic_scenario_references_are_coherent() -> None:
    scenario = get_historical_jakarta()
    facilities = {facility.id: facility for facility in scenario.facilities}
    products = {product.id: product for product in scenario.products}
    materials = {material.id: material for material in scenario.materials}
    assert all(material.supplier_id in facilities for material in scenario.materials)
    assert all(item.material_id in materials for product in scenario.products for item in product.bom)
    assert all(set(product.substitute_product_ids) <= products.keys() for product in scenario.products)
    assert all(item.facility_id in facilities and item.product_id in products for item in scenario.inventory)
    assert all(
        order.store_id in facilities and order.product_id in products and order.preferred_warehouse_id in facilities
        for order in scenario.orders
    )


def test_geojson_and_graph_are_consistent() -> None:
    roads = get_road_features()
    graph = get_routing_graph()
    flood = get_historical_flood_extent()
    segment_ids = {feature["properties"]["segmentId"] for feature in roads["features"]}
    roads_by_id = {feature["properties"]["segmentId"]: feature for feature in roads["features"]}
    assert {edge["segmentId"] for edge in graph["edges"]} == segment_ids
    assert len(graph["edges"]) == 1_413
    assert sum(edge["bidirectional"] for edge in graph["edges"]) == 135
    assert all(
        edge["bidirectional"] is (not roads_by_id[edge["segmentId"]]["properties"]["oneway"]) for edge in graph["edges"]
    )
    assert graph["metadata"]["source"] == "OpenStreetMap contributors"
    assert graph["metadata"]["license"] == "ODbL 1.0"
    assert graph["metadata"]["fullGraph"]["nodes"] == 64053
    assert graph["metadata"]["processedGraph"]["uniqueSegments"] == len(segment_ids)
    assert graph["metadata"]["processedGraph"]["directedEdges"] == 1_548
    assert len(graph["metadata"]["facilityNodeMappings"]) == 10
    node_ids = {node["id"] for node in graph["nodes"]}
    assert set(graph["metadata"]["facilityNodeMappings"].values()) <= node_ids
    assert flood["features"][0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    for feature in roads["features"]:
        assert feature["geometry"]["type"] == "LineString"
        assert feature["properties"]["osmWayIds"]
        assert feature["properties"]["travelTimeMinutes"] > 0
        assert all(
            100 < coordinate[0] < 120 and -10 < coordinate[1] < 0 for coordinate in feature["geometry"]["coordinates"]
        )


def test_compact_edge_record_preserves_normalized_osmnx_directionality() -> None:
    bidirectional = routing_edge_record(source="u", target="v", segment_id="road-two-way", oneway=False)
    one_way = routing_edge_record(source="u", target="v", segment_id="road-one-way", oneway=True)

    assert bidirectional["bidirectional"] is True
    assert one_way["bidirectional"] is False


def test_runtime_graph_respects_bidirectional_and_one_way_controls() -> None:
    runtime_graph = _build_graph({})

    bidirectional_segment = "osm-332341344-5506920631-0"  # Jalan Duri Tol Raya
    assert runtime_graph["332341344"]["5506920631"]["segment_id"] == bidirectional_segment
    assert runtime_graph["5506920631"]["332341344"]["segment_id"] == bidirectional_segment

    one_way_segment = "osm-29938988-6552109327-0"  # Jalan Kebon Sirih
    assert runtime_graph["29938988"]["6552109327"]["segment_id"] == one_way_segment
    assert not runtime_graph.has_edge("6552109327", "29938988")
    assert runtime_graph.number_of_edges() == 1_548


def test_model_inference_uses_historical_probability_and_real_label_metadata() -> None:
    road = get_road_features()["features"][1]["properties"]
    result = predict_risk(road)
    assert 0 <= result.riskProbability <= 1
    assert result.riskLevel in {"low", "medium", "high", "critical"}
    metrics_path = Path(__file__).resolve().parents[1] / "app" / "models" / "flood_risk_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["version"] == "indonesia-road-corridor-flood-exposure-v1"
    assert metrics["selectedModel"] == "randomForest"
    assert metrics["split"]["test"]["regions"] == ["gaul2-73682", "gaul2-73814", "gaul2-73847"]
