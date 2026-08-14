from __future__ import annotations

from fastapi.testclient import TestClient


def test_dynamic_api_contract_and_errors(client: TestClient) -> None:
    payload = {
        "scenarioId": "scenario-jakarta-20250304",
        "analysisMode": "scenario-simulation",
        "region": "jakarta",
        "rainfallScenario": "Q3",
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 201
    simulation = response.json()
    assert simulation["analysisMode"] == "scenario-simulation"
    assert simulation["region"] == "jakarta"
    assert simulation["hazard"]["rainfallScenario"] == "Q3"
    assert simulation["hazard"]["probabilityCalibrated"] is False
    assert simulation["hazard"]["fusionMethod"] == "logit_shift"
    disruption = client.get(f"/api/simulations/{simulation['id']}/disruption")
    assert disruption.status_code == 200
    roads = disruption.json()["roads"]
    assert len(roads) == 1413
    assert all("dynamicRoadRiskScore" in road for road in roads)
    recovery = client.post(f"/api/simulations/{simulation['id']}/recovery", json={})
    assert recovery.status_code == 201
    assert recovery.json()["simulationId"] == simulation["id"]

    cases = [
        ({**payload, "analysisMode": "future"}, "UNKNOWN_ANALYSIS_MODE"),
        ({**payload, "region": "surabaya"}, "UNSUPPORTED_REGION"),
        ({**payload, "rainfallScenario": "Q5"}, "UNKNOWN_RAINFALL_SCENARIO"),
    ]
    for invalid_payload, code in cases:
        error = client.post("/api/simulations", json=invalid_payload)
        assert error.status_code == 422
        assert error.json()["code"] == code
        assert error.json()["retryable"] is False


def test_historical_api_default_has_no_dynamic_hazard(client: TestClient) -> None:
    response = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["analysisMode"] == "historical-replay"
    assert "hazard" not in payload
    disruption = client.get(f"/api/simulations/{payload['id']}/disruption").json()
    assert all("dynamicRoadRiskScore" not in road for road in disruption["roads"])
