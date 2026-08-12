from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recovery_flow_returns_expected_actions() -> None:
    # 1. Create a simulation
    sim_resp = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert sim_resp.status_code == 201
    sim_id = sim_resp.json()["id"]

    # 2. Get disruption to ensure it's calculated
    dis_resp = client.get(f"/api/simulations/{sim_id}/disruption")
    assert dis_resp.status_code == 200

    # 3. Request recovery plan
    rec_resp = client.post(
        f"/api/simulations/{sim_id}/recovery",
        json={"constraints": {"allowSubstitution": True}}
    )
    assert rec_resp.status_code == 201
    recovery = rec_resp.json()

    assert recovery["status"] in ["ready", "partial"]
    assert recovery["simulationId"] == sim_id
    assert "summary" in recovery
    assert "risksMitigated" in recovery["summary"]

    # At least some manufacturing/commerce/logistics actions should be generated
    assert isinstance(recovery["manufacturingActions"], list)
    assert isinstance(recovery["commerceActions"], list)
    assert isinstance(recovery["logisticsActions"], list)
    
    # 4. Get impact comparison
    imp_resp = client.get(f"/api/simulations/{sim_id}/impact")
    assert imp_resp.status_code == 200
    impact = imp_resp.json()
    
    assert impact["simulationId"] == sim_id
    assert "metrics" in impact
    assert "actionCounts" in impact
    
    metrics = {m["key"]: m for m in impact["metrics"]}
    assert "orders-fulfilled" in metrics
    assert "sales-exposure-risk" in metrics
    assert metrics["sales-exposure-risk"]["currency"] == "IDR"

    assert impact["actionCounts"]["manufacturing"] == len(recovery["manufacturingActions"])
    assert impact["actionCounts"]["logistics"] == len(recovery["logisticsActions"])
    assert impact["actionCounts"]["commerce"] == len(recovery["commerceActions"])
