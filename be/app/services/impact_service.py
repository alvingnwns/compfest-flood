from app.core.exceptions import DomainError, conflict
from app.engines.impact import ImpactEngine
from app.schemas.impact import ImpactComparison
from app.schemas.recovery import RecoveryResult
from app.services.recovery_service import RecoveryService
from app.services.scenario_service import ScenarioService
from app.services.simulation_service import SimulationService


class ImpactService:
    def __init__(
        self,
        scenarios: ScenarioService,
        simulations: SimulationService,
        recovery: RecoveryService,
        impact: ImpactEngine,
    ) -> None:
        self._scenarios = scenarios
        self._simulations = simulations
        self._recovery = recovery
        self._impact = impact

    def get(self, simulation_id: str) -> ImpactComparison:
        simulation = self._simulations.get(simulation_id)
        try:
            recovery = self._recovery.get(simulation_id)
        except DomainError as exc:
            if exc.code == "recovery_not_found":
                raise conflict("recovery_not_completed", "Recovery plan is not completed.") from exc
            raise
        if not isinstance(recovery, RecoveryResult):
            raise conflict("recovery_not_completed", "Recovery plan is not completed.")
        scenario = self._scenarios.get(simulation.scenario_id)
        return self._impact.compare(simulation_id, scenario, recovery)
