from dataclasses import dataclass

from fastapi import Request

from app.core.config import Settings
from app.engines.flood_risk import StubFloodRiskEngine
from app.engines.impact import StubImpactEngine
from app.engines.optimizer import StubRecoveryOptimizer
from app.engines.routing import StubRoutingEngine
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.simulation_repository import InMemorySimulationRepository
from app.services.disruption_service import DisruptionService
from app.services.impact_service import ImpactService
from app.services.recovery_service import RecoveryService
from app.services.scenario_service import ScenarioService
from app.services.simulation_service import SimulationService


@dataclass(frozen=True)
class Container:
    scenarios: ScenarioService
    simulations: SimulationService
    disruption: DisruptionService
    recovery: RecoveryService
    impact: ImpactService


def build_container(settings: Settings) -> Container:
    fixtures = FixtureRepository(settings.data_dir)
    scenario_repository = ScenarioRepository(settings.data_dir)
    simulation_repository = InMemorySimulationRepository()
    flood_risk = StubFloodRiskEngine(fixtures)
    routing = StubRoutingEngine(fixtures)
    impact_engine = StubImpactEngine(fixtures)
    optimizer = StubRecoveryOptimizer(fixtures)
    scenarios = ScenarioService(scenario_repository)
    simulations = SimulationService(scenarios, simulation_repository, flood_risk, optimizer)
    disruption = DisruptionService(scenarios, simulations, flood_risk, routing, impact_engine, fixtures)
    recovery = RecoveryService(scenarios, simulations, simulation_repository, disruption, optimizer)
    impact = ImpactService(scenarios, simulations, recovery, impact_engine)
    return Container(
        scenarios=scenarios, simulations=simulations, disruption=disruption, recovery=recovery, impact=impact
    )


def get_container(request: Request) -> Container:
    return request.app.state.container
