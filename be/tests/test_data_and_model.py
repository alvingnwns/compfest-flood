import json
from pathlib import Path

from app.repositories.geospatial_repository import get_historical_flood_extent, get_road_features, get_routing_graph
from app.repositories.scenario_repository import get_historical_jakarta
from app.services.flood_risk_service import predict_risk


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
    assert {edge["segmentId"] for edge in graph["edges"]} == segment_ids
    assert graph["metadata"]["source"] == "OpenStreetMap contributors"
    assert graph["metadata"]["license"] == "ODbL 1.0"
    assert graph["metadata"]["fullGraph"]["nodes"] == 64053
    assert graph["metadata"]["processedGraph"]["uniqueSegments"] == len(segment_ids)
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


def test_model_inference_uses_raw_probability_and_synthetic_metadata() -> None:
    road = get_road_features()["features"][1]["properties"]
    result = predict_risk(road)
    assert 0 <= result.riskProbability <= 1
    assert result.riskLevel in {"low", "medium", "high", "critical"}
    metrics_path = Path(__file__).resolve().parents[1] / "app" / "models" / "flood_risk_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert "synthetic" in metrics["description"].lower()
