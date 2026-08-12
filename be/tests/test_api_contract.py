from fastapi.testclient import TestClient


def test_startup_health_and_cors(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "engineMode": "connected"}
    response = client.options(
        "/api/simulations",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_complete_seven_endpoint_contract_flow(client: TestClient) -> None:
    scenario_response = client.get("/api/scenarios/historical-jakarta")
    assert scenario_response.status_code == 200
    scenario = scenario_response.json()
    assert scenario["mode"] == "historical-replay"
    assert scenario["dataSources"]["historicalStatus"] == "offline_snapshot"

    created = client.post("/api/simulations", json={"scenarioId": scenario["id"]})
    assert created.status_code == 201
    simulation = created.json()
    assert simulation["status"] == "completed"
    assert simulation["modelVersion"] == "indonesia-road-corridor-flood-exposure-v1"
    assert simulation["optimizerVersion"] == "cp-sat-connected-v2"
    simulation_id = simulation["id"]
    assert client.get(f"/api/simulations/{simulation_id}").json() == simulation

    disruption = client.get(f"/api/simulations/{simulation_id}/disruption").json()
    assert disruption["simulationId"] == simulation_id
    assert len(disruption["roads"]) > 1_000
    assert {route["type"] for route in disruption["routes"]} <= {"baseline", "recovery"}
    assert "baseline" in {route["type"] for route in disruption["routes"]}
    assert all(0 <= road["riskProbability"] <= 1 for road in disruption["roads"])

    generated = client.post(
        f"/api/simulations/{simulation_id}/recovery",
        json={"constraints": {"allowSubstitution": True, "maxAdditionalDelayMinutes": 30}},
    )
    assert generated.status_code == 201
    recovery = generated.json()
    assert recovery["status"] in {"ready", "partial"}
    assert len(recovery["commerceActions"]) == len(scenario["orders"])
    assert {action["action"] for action in recovery["commerceActions"]} <= {
        "fulfill",
        "split",
        "delay",
        "substitute",
        "prioritize",
        "split-substitute",
    }
    required_logistics = {
        "baselineRouteId",
        "recoveryRouteId",
        "baselineEtaMinutes",
        "recoveryEtaMinutes",
        "baselineFloodExposure",
        "recoveryFloodExposure",
    }
    assert all(required_logistics <= action.keys() for action in recovery["logisticsActions"])
    assert client.get(f"/api/simulations/{simulation_id}/recovery").json() == recovery

    impact = client.get(f"/api/simulations/{simulation_id}/impact").json()
    assert [metric["key"] for metric in impact["metrics"]] == [
        "orders-fulfilled",
        "on-time-delivery",
        "failed-orders",
        "average-delay",
        "sales-exposure-risk",
    ]
    assert impact["metrics"][1]["baseline"] <= 1
    assert impact["metrics"][1]["recovery"] <= 1


def test_structured_errors_and_validation(client: TestClient, simulation_id: str) -> None:
    missing = client.get("/api/simulations/sim-missing")
    assert missing.status_code == 404
    assert missing.json() == {
        "code": "simulation_not_found",
        "message": "Simulation not found.",
        "retryable": False,
        "details": {"simulationId": "sim-missing"},
    }
    malformed = client.post("/api/simulations", content="{", headers={"content-type": "application/json"})
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "invalid_request"
    invalid = client.post(
        f"/api/simulations/{simulation_id}/recovery",
        json={"constraints": {"maxAdditionalDelayMinutes": -1}},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"


def test_impact_and_recovery_use_conflict_before_generation(client: TestClient, simulation_id: str) -> None:
    for suffix in ("recovery", "impact"):
        response = client.get(f"/api/simulations/{simulation_id}/{suffix}")
        assert response.status_code == 409
        assert response.json()["code"] == "recovery_not_ready"


def test_process_local_idempotency(client: TestClient) -> None:
    payload = {"scenarioId": "scenario-jakarta-20250304"}
    first = client.post("/api/simulations", json=payload).json()
    second = client.post("/api/simulations", json=payload).json()
    assert first["id"] == second["id"]
    recovery_payload = {"constraints": {"allowSubstitution": True, "maxAdditionalDelayMinutes": 30}}
    first_plan = client.post(f"/api/simulations/{first['id']}/recovery", json=recovery_payload).json()
    second_plan = client.post(f"/api/simulations/{first['id']}/recovery", json=recovery_payload).json()
    assert first_plan["id"] == second_plan["id"]


def test_no_feasible_api_shape_matches_recovery_result_contract(
    client: TestClient, simulation_id: str, monkeypatch
) -> None:
    from app.api import simulations as simulations_api
    from app.repositories.scenario_repository import get_historical_jakarta

    infeasible = get_historical_jakarta().model_copy(deep=True)
    for material in infeasible.materials:
        material.available_quantity = 0
    for inventory in infeasible.inventory:
        inventory.quantity = 0
    monkeypatch.setattr(simulations_api, "get_historical_jakarta", lambda: infeasible)
    response = client.post(
        f"/api/simulations/{simulation_id}/recovery",
        json={"constraints": {"allowSubstitution": False, "maxAdditionalDelayMinutes": 30}},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "no-feasible-plan"
    assert payload["completedAt"]
    assert payload["summary"]["recoverableOrders"] == 0
    assert payload["manufacturingActions"] == []
    assert payload["logisticsActions"] == []
    assert payload["commerceActions"] == []
    assert payload["possibleNextActions"]
    assert payload["error"]["code"] == "no_feasible_plan"
