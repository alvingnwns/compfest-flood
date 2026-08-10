from typing import Protocol

from app.repositories.fixture_repository import FixtureRepository
from app.schemas.disruption import RoadRisk
from app.schemas.scenario import Scenario


class FloodRiskEngine(Protocol):
    version: str

    def predict(self, scenario: Scenario) -> list[RoadRisk]: ...


class StubFloodRiskEngine:
    version = "stub-flood-risk-v1"

    def __init__(self, fixtures: FixtureRepository) -> None:
        self._fixtures = fixtures

    def predict(self, scenario: Scenario) -> list[RoadRisk]:
        del scenario
        return [RoadRisk.model_validate(item) for item in self._fixtures.load("disruption")["roads"]]
