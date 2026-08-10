from fastapi.testclient import TestClient


def test_health_and_startup(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "engineMode": "stub"}


def test_cors_allows_only_configured_frontend(client: TestClient) -> None:
    response = client.options(
        "/api/scenarios/historical-jakarta",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
