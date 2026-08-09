from datetime import UTC, datetime
from uuid import uuid4

from app.engines.flood_risk import FloodRiskEngine
from app.engines.optimizer import RecoveryOptimizer
from app.repositories.simulation_repository import InMemorySimulationRepository
from app.schemas.simulation import Simulation, SimulationStatus
from app.services.scenario_service import ScenarioService


class SimulationService:
    def __init__(
        self,
        scenarios: ScenarioService,
        simulations: InMemorySimulationRepository,
        flood_risk: FloodRiskEngine,
        optimizer: RecoveryOptimizer,
    ) -> None:
        self._scenarios = scenarios
        self._simulations = simulations
        self._flood_risk = flood_risk
        self._optimizer = optimizer

    def create(self, scenario_id: str) -> Simulation:
        scenario = self._scenarios.get(scenario_id)
        existing = self._simulations.get_by_scenario(scenario_id)
        if existing and existing.status == SimulationStatus.COMPLETED:
            return existing

        created_at = datetime.now(UTC)
        simulation = Simulation(
            id=f"sim-{uuid4().hex[:12]}",
            scenario_id=scenario.id,
            status=SimulationStatus.QUEUED,
            created_at=created_at,
            data_mode=scenario.data_sources.mode,
            historical_data_status=scenario.data_sources.historical_status,
        )
        self._simulations.save(simulation)
        simulation.status = SimulationStatus.PROCESSING
        self._simulations.save(simulation)

        # Foundation engines are deterministic and synchronous. Lifecycle states remain contract-compatible.
        simulation.status = SimulationStatus.COMPLETED
        simulation.completed_at = datetime.now(UTC)
        simulation.model_version = self._flood_risk.version
        simulation.optimizer_version = self._optimizer.version
        return self._simulations.save(simulation)

    def get(self, simulation_id: str) -> Simulation:
        simulation = self._simulations.get(simulation_id)
        if simulation is None:
            from app.core.exceptions import not_found

            raise not_found("simulation", simulation_id)
        return simulation
