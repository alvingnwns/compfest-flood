from typing import Protocol

from app.repositories.fixture_repository import FixtureRepository
from app.schemas.disruption import OperationalImpact
from app.schemas.impact import ImpactComparison
from app.schemas.recovery import RecoveryResult
from app.schemas.scenario import Scenario


class ImpactEngine(Protocol):
    def analyze_operational_impact(self, scenario: Scenario) -> OperationalImpact: ...

    def compare(self, simulation_id: str, scenario: Scenario, recovery: RecoveryResult) -> ImpactComparison: ...


class StubImpactEngine:
    def __init__(self, fixtures: FixtureRepository) -> None:
        self._fixtures = fixtures

    def analyze_operational_impact(self, scenario: Scenario) -> OperationalImpact:
        del scenario
        return OperationalImpact.model_validate(self._fixtures.load("disruption")["impact"])

    def compare(self, simulation_id: str, scenario: Scenario, recovery: RecoveryResult) -> ImpactComparison:
        del scenario, recovery
        return ImpactComparison.model_validate({"simulationId": simulation_id, **self._fixtures.load("impact")})
