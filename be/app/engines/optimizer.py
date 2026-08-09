from datetime import datetime
from typing import Protocol

from app.core.exceptions import DomainError
from app.repositories.fixture_repository import FixtureRepository
from app.schemas.disruption import DisruptionAnalysis
from app.schemas.recovery import RecoveryConstraints, RecoveryResult
from app.schemas.scenario import Scenario


class RecoveryOptimizer(Protocol):
    version: str

    def generate(
        self,
        simulation_id: str,
        scenario: Scenario,
        disruption: DisruptionAnalysis,
        constraints: RecoveryConstraints | None,
        created_at: datetime,
    ) -> RecoveryResult: ...


class StubRecoveryOptimizer:
    version = "stub-recovery-v1"

    def __init__(self, fixtures: FixtureRepository) -> None:
        self._fixtures = fixtures

    def generate(
        self,
        simulation_id: str,
        scenario: Scenario,
        disruption: DisruptionAnalysis,
        constraints: RecoveryConstraints | None,
        created_at: datetime,
    ) -> RecoveryResult:
        del scenario, disruption
        if constraints and constraints.allow_substitution is False:
            raise DomainError(
                status_code=422,
                code="unsupported_stub_constraint",
                message="The development optimizer currently requires substitution to remain enabled.",
                details={"allowSubstitution": False},
            )
        return RecoveryResult.model_validate(
            {
                "id": f"plan-{simulation_id}",
                "simulationId": simulation_id,
                "createdAt": created_at,
                "completedAt": datetime.now(created_at.tzinfo),
                **self._fixtures.load("recovery"),
            }
        )
