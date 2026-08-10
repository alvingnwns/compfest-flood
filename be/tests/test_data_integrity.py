import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.disruption import RoadRisk
from app.schemas.impact import OnTimeDeliveryMetric


def test_scenario_references_are_coherent(client: TestClient) -> None:
    scenario = client.get("/api/scenarios/historical-jakarta").json()
    facilities = {facility["id"]: facility for facility in scenario["facilities"]}
    products = {product["id"] for product in scenario["products"]}
    assert all(material["supplierId"] in facilities for material in scenario["materials"])
    assert all(set(material["productIds"]).issubset(products) for material in scenario["materials"])
    assert all(order["storeId"] in facilities and order["productId"] in products for order in scenario["orders"])


def test_disruption_geojson_and_references_are_coherent(client: TestClient, simulation_id: str) -> None:
    scenario = client.get("/api/scenarios/historical-jakarta").json()
    disruption = client.get(f"/api/simulations/{simulation_id}/disruption").json()
    facilities = {facility["id"] for facility in scenario["facilities"]}
    orders = {order["id"] for order in scenario["orders"]}
    road_ids = {road["segmentId"] for road in disruption["roads"]}
    assert disruption["historicalFloodGeometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert {road["geometry"]["type"] for road in disruption["roads"]} == {"LineString", "MultiLineString"}
    assert all(
        route["originFacilityId"] in facilities and route["destinationFacilityId"] in facilities
        for route in disruption["routes"]
    )
    assert all(set(route["affectedRoadSegmentIds"]).issubset(road_ids) for route in disruption["routes"])
    assert set(disruption["impact"]["impactedOrderIds"]).issubset(orders)


def test_probability_and_rate_bounds_are_enforced() -> None:
    with pytest.raises(ValidationError):
        OnTimeDeliveryMetric(key="on-time-delivery", baseline=0.5, recovery=1.2)
    with pytest.raises(ValidationError):
        RoadRisk.model_validate(
            {
                "segmentId": "road-invalid",
                "roadName": "Invalid",
                "geometry": {"type": "LineString", "coordinates": [[106.8, -6.1], [106.9, -6.2]]},
                "riskProbability": 1.2,
                "riskLevel": "high",
                "estimatedDelayMinutes": 1,
                "riskFactors": [],
                "affectedSupplierIds": [],
                "affectedWarehouseIds": [],
                "affectedOrderIds": [],
            }
        )
