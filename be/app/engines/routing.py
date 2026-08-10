from typing import Protocol

from app.repositories.fixture_repository import FixtureRepository
from app.schemas.disruption import Route
from app.schemas.scenario import Scenario


class RoutingEngine(Protocol):
    def build_routes(self, scenario: Scenario) -> list[Route]: ...


class StubRoutingEngine:
    def __init__(self, fixtures: FixtureRepository) -> None:
        self._fixtures = fixtures

    def build_routes(self, scenario: Scenario) -> list[Route]:
        del scenario
        return [Route.model_validate(item) for item in self._fixtures.load("disruption")["routes"]]
