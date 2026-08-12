from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.simulation_repository import simulation_repository


@pytest.fixture
def client() -> Iterator[TestClient]:
    simulation_repository.clear()
    data_dir = Path(__file__).resolve().parents[1] / "data"
    with TestClient(create_app(Settings(app_env="test", data_dir=data_dir))) as test_client:
        yield test_client
    simulation_repository.clear()


@pytest.fixture
def simulation_id(client: TestClient) -> str:
    response = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert response.status_code == 201
    return response.json()["id"]
