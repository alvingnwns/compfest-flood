from fastapi.testclient import TestClient


def test_unknown_simulation_uses_structured_error(client: TestClient) -> None:
    response = client.get("/api/simulations/sim-missing")
    assert response.status_code == 404
    assert response.json() == {
        "code": "simulation_not_found",
        "message": "Simulation not found.",
        "retryable": False,
        "details": {"simulationId": "sim-missing"},
    }


def test_request_validation_uses_structured_error(client: TestClient) -> None:
    response = client.post("/api/simulations", json={"scenarioId": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["retryable"] is False
    assert body["details"]["errors"]


def test_unknown_scenario_uses_structured_error(client: TestClient) -> None:
    response = client.post("/api/simulations", json={"scenarioId": "scenario-missing"})
    assert response.status_code == 404
    assert response.json()["code"] == "scenario_not_found"


def test_recovery_must_be_generated_before_retrieval(client: TestClient, simulation_id: str) -> None:
    response = client.get(f"/api/simulations/{simulation_id}/recovery")
    assert response.status_code == 404
    assert response.json()["code"] == "recovery_not_found"


def test_impact_requires_completed_recovery(client: TestClient, simulation_id: str) -> None:
    response = client.get(f"/api/simulations/{simulation_id}/impact")
    assert response.status_code == 409
    assert response.json()["code"] == "recovery_not_completed"


def test_stub_reports_unsupported_constraint_honestly(client: TestClient, simulation_id: str) -> None:
    response = client.post(
        f"/api/simulations/{simulation_id}/recovery", json={"constraints": {"allowSubstitution": False}}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_stub_constraint"
