from pydantic import TypeAdapter

from app.core.exceptions import conflict
from app.engines.flood_risk import FloodRiskEngine
from app.engines.impact import ImpactEngine
from app.engines.routing import RoutingEngine
from app.repositories.fixture_repository import FixtureRepository
from app.schemas.common import PolygonalGeometry
from app.schemas.disruption import DisruptionAnalysis
from app.schemas.simulation import SimulationStatus
from app.services.scenario_service import ScenarioService
from app.services.simulation_service import SimulationService


class DisruptionService:
    def __init__(
        self,
        scenarios: ScenarioService,
        simulations: SimulationService,
        flood_risk: FloodRiskEngine,
        routing: RoutingEngine,
        impact: ImpactEngine,
        fixtures: FixtureRepository,
    ) -> None:
        self._scenarios = scenarios
        self._simulations = simulations
        self._flood_risk = flood_risk
        self._routing = routing
        self._impact = impact
        self._fixtures = fixtures

    def get(self, simulation_id: str) -> DisruptionAnalysis:
        simulation = self._simulations.get(simulation_id)
        if simulation.status != SimulationStatus.COMPLETED:
            raise conflict("simulation_not_completed", "Simulation analysis is not completed.")
        scenario = self._scenarios.get(simulation.scenario_id)
        analysis = DisruptionAnalysis(
            simulation_id=simulation.id,
            facilities=scenario.facilities,
            roads=self._flood_risk.predict(scenario),
            routes=self._routing.build_routes(scenario),
            historical_flood_geometry=TypeAdapter(PolygonalGeometry).validate_python(
                self._fixtures.load("disruption")["historicalFloodGeometry"]
            ),
            impact=self._impact.analyze_operational_impact(scenario),
        )
        self._validate_references(analysis, scenario)
        return analysis

    @staticmethod
    def _validate_references(analysis: DisruptionAnalysis, scenario: object) -> None:
        facility_ids = {facility.id for facility in analysis.facilities}
        supplier_ids = {facility.id for facility in analysis.facilities if facility.kind == "supplier"}
        warehouse_ids = {facility.id for facility in analysis.facilities if facility.kind == "warehouse"}
        order_ids = {order.id for order in scenario.orders}  # type: ignore[attr-defined]
        road_ids = {road.segment_id for road in analysis.roads}
        for road in analysis.roads:
            if not set(road.affected_supplier_ids).issubset(supplier_ids):
                raise ValueError(f"Road {road.segment_id} references an invalid supplier")
            if not set(road.affected_warehouse_ids).issubset(warehouse_ids):
                raise ValueError(f"Road {road.segment_id} references an invalid warehouse")
            if not set(road.affected_order_ids).issubset(order_ids):
                raise ValueError(f"Road {road.segment_id} references an invalid order")
        for route in analysis.routes:
            if route.origin_facility_id not in facility_ids or route.destination_facility_id not in facility_ids:
                raise ValueError(f"Route {route.id} references an invalid facility")
            if not set(route.affected_road_segment_ids).issubset(road_ids):
                raise ValueError(f"Route {route.id} references an invalid road")
        if not set(analysis.impact.impacted_supplier_ids).issubset(supplier_ids):
            raise ValueError("Operational impact references an invalid supplier")
        if not set(analysis.impact.impacted_warehouse_ids).issubset(warehouse_ids):
            raise ValueError("Operational impact references an invalid warehouse")
        if not set(analysis.impact.impacted_order_ids).issubset(order_ids):
            raise ValueError("Operational impact references an invalid order")
