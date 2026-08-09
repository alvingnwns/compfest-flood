from fastapi.testclient import TestClient


def test_seven_endpoint_contract_flow(client: TestClient) -> None:
    scenario_response = client.get("/api/scenarios/historical-jakarta")
    assert scenario_response.status_code == 200
    scenario = scenario_response.json()
    assert scenario["id"] == "scenario-jakarta-20250304"
    assert scenario["dataSources"]["mode"] == "historical_snapshot"

    create_response = client.post("/api/simulations", json={"scenarioId": scenario["id"]})
    assert create_response.status_code == 201
    simulation = create_response.json()
    simulation_id = simulation["id"]
    assert simulation["status"] == "completed"
    assert simulation["modelVersion"] == "stub-flood-risk-v1"
    assert simulation["optimizerVersion"] == "stub-recovery-v1"
    assert "error" not in simulation

    status_response = client.get(f"/api/simulations/{simulation_id}")
    assert status_response.status_code == 200
    assert status_response.json()["id"] == simulation_id

    disruption_response = client.get(f"/api/simulations/{simulation_id}/disruption")
    assert disruption_response.status_code == 200
    disruption = disruption_response.json()
    assert disruption["simulationId"] == simulation_id
    assert disruption["roads"][0]["riskProbability"] == 0.82

    generation_response = client.post(f"/api/simulations/{simulation_id}/recovery", json={})
    assert generation_response.status_code == 201
    assert generation_response.json()["status"] == "partial"

    recovery_response = client.get(f"/api/simulations/{simulation_id}/recovery")
    assert recovery_response.status_code == 200
    assert recovery_response.json()["summary"]["recoverableOrders"] == 18

    impact_response = client.get(f"/api/simulations/{simulation_id}/impact")
    assert impact_response.status_code == 200
    impact = impact_response.json()
    assert len(impact["metrics"]) == 5
    assert next(metric for metric in impact["metrics"] if metric["key"] == "on-time-delivery")["recovery"] == 0.85


def test_development_posts_are_idempotent(client: TestClient) -> None:
    first = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"}).json()
    second = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"}).json()
    assert first["id"] == second["id"]

    first_plan = client.post(f"/api/simulations/{first['id']}/recovery", json={}).json()
    second_plan = client.post(f"/api/simulations/{first['id']}/recovery", json={}).json()
    assert first_plan["id"] == second_plan["id"]
