from fastapi.testclient import TestClient

from app.main import app
from app.repositories.simulation_repository import simulation_repository

client = TestClient(app)


def setup_function() -> None:
    simulation_repository.clear()


def test_create_and_retrieve_completed_historical_simulation() -> None:
    created = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})

    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "completed"
    assert payload["scenarioId"] == "scenario-jakarta-20250304"
    assert payload["dataMode"] == "historical_snapshot"
    assert payload["historicalDataStatus"] == "offline_snapshot"
    assert payload["createdAt"].endswith(("Z", "+00:00"))
    assert payload["completedAt"].endswith(("Z", "+00:00"))

    fetched = client.get(f"/api/simulations/{payload['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == payload


def test_unknown_scenario_returns_contract_error() -> None:
    response = client.post("/api/simulations", json={"scenarioId": "scenario-missing"})

    assert response.status_code == 404
    assert response.json() == {
        "code": "scenario_not_found",
        "message": "Scenario not found.",
        "retryable": False,
        "details": {"scenarioId": "scenario-missing"},
    }


def test_empty_scenario_id_is_semantically_invalid() -> None:
    response = client.post("/api/simulations", json={"scenarioId": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_missing_simulation_returns_contract_error() -> None:
    response = client.get("/api/simulations/sim-missing")

    assert response.status_code == 404
    assert response.json()["code"] == "simulation_not_found"


def test_disruption_endpoint_returns_analysis() -> None:
    # 1. Create a simulation
    created = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert created.status_code == 201
    sim_id = created.json()["id"]

    # 2. Get disruption
    response = client.get(f"/api/simulations/{sim_id}/disruption")
    assert response.status_code == 200
    payload = response.json()
    
    assert payload["simulationId"] == sim_id
    assert "facilities" in payload
    assert "historicalFloodGeometry" in payload
    assert "roads" in payload
    assert "routes" in payload
    assert "impact" in payload
    
    # 3. Check impact summary structure
    impact = payload["impact"]
    assert "impactedSupplierIds" in impact
    assert "roadSegmentsAtRisk" in impact
    assert "salesExposure" in impact
    assert impact["salesExposure"]["currency"] == "IDR"

