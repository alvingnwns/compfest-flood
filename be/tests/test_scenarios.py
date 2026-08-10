from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_historical_jakarta_snapshot_matches_frontend_contract_shape() -> None:
    response = client.get("/api/scenarios/historical-jakarta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "scenario-jakarta-20250304"
    assert payload["mode"] == "historical-replay"
    assert payload["eventDate"] == "2025-03-04"
    assert payload["dataSources"]["mode"] == "historical_snapshot"
    assert payload["dataSources"]["historicalStatus"] == "offline_snapshot"
    assert len(payload["vehicles"]) == 3
    assert len(payload["products"]) == 2
    assert len(payload["orders"]) == 20


def test_snapshot_references_only_known_entities() -> None:
    payload = client.get("/api/scenarios/historical-jakarta").json()
    facility_ids = {facility["id"] for facility in payload["facilities"]}
    product_ids = {product["id"] for product in payload["products"]}

    assert all(material["supplierId"] in facility_ids for material in payload["materials"])
    assert all(product_id in product_ids for material in payload["materials"] for product_id in material["productIds"])
    assert all(item["facilityId"] in facility_ids and item["productId"] in product_ids for item in payload["inventory"])
    assert all(order["storeId"] in facility_ids and order["productId"] in product_ids for order in payload["orders"])
