from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.business_import.repository import business_snapshot_repository
from app.core.config import Settings
from app.main import create_app
from app.repositories.simulation_repository import simulation_repository


@pytest.fixture
def client() -> Iterator[TestClient]:
    simulation_repository.clear()
    business_snapshot_repository.clear()
    data_dir = Path(__file__).resolve().parents[1] / "data"
    settings = Settings(
        app_env="test",
        data_dir=data_dir,
        gemini_api_key=SecretStr(""),
        openrouter_api_key=SecretStr(""),
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
    simulation_repository.clear()
    business_snapshot_repository.clear()


@pytest.fixture
def simulation_id(client: TestClient) -> str:
    response = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert response.status_code == 201
    return response.json()["id"]
