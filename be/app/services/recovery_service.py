from datetime import UTC, datetime

from app.core.exceptions import not_found
from app.engines.optimizer import RecoveryOptimizer
from app.repositories.simulation_repository import InMemorySimulationRepository
from app.schemas.recovery import RecoveryConstraints, RecoveryPlan, RecoveryResult
from app.schemas.simulation import SimulationStatus
from app.services.disruption_service import DisruptionService
from app.services.scenario_service import ScenarioService
from app.services.simulation_service import SimulationService


class RecoveryService:
    def __init__(
        self,
        scenarios: ScenarioService,
        simulations: SimulationService,
        simulation_repository: InMemorySimulationRepository,
        disruption: DisruptionService,
        optimizer: RecoveryOptimizer,
    ) -> None:
        self._scenarios = scenarios
        self._simulations = simulations
        self._repository = simulation_repository
        self._disruption = disruption
        self._optimizer = optimizer

    def create(self, simulation_id: str, constraints: RecoveryConstraints | None) -> RecoveryPlan:
        simulation = self._simulations.get(simulation_id)
        if simulation.status != SimulationStatus.COMPLETED:
            from app.core.exceptions import conflict

            raise conflict("simulation_not_completed", "Simulation analysis is not completed.")
        existing = self._repository.get_recovery(simulation_id)
        if existing is not None:
            return existing
        scenario = self._scenarios.get(simulation.scenario_id)
        recovery = self._optimizer.generate(
            simulation.id, scenario, self._disruption.get(simulation.id), constraints, datetime.now(UTC)
        )
        self._validate_references(recovery, scenario, self._disruption.get(simulation.id))
        return self._repository.save_recovery(simulation_id, recovery)

    def get(self, simulation_id: str) -> RecoveryPlan:
        self._simulations.get(simulation_id)
        recovery = self._repository.get_recovery(simulation_id)
        if recovery is None:
            raise not_found("recovery", simulation_id)
        return recovery

    @staticmethod
    def _validate_references(recovery: RecoveryResult, scenario: object, disruption: object) -> None:
        products = {product.id for product in scenario.products}  # type: ignore[attr-defined]
        facilities = {facility.id: facility for facility in scenario.facilities}  # type: ignore[attr-defined]
        orders = {order.id: order for order in scenario.orders}  # type: ignore[attr-defined]
        vehicles = {vehicle.id for vehicle in scenario.vehicles}  # type: ignore[attr-defined]
        routes = {route.id for route in disruption.routes}  # type: ignore[attr-defined]
        for action in recovery.manufacturing_actions:
            if action.product_id not in products:
                raise ValueError(f"Manufacturing action {action.id} references an invalid product")
        for action in recovery.logistics_actions:
            if (
                action.order_id not in orders
                or action.original_warehouse_id not in facilities
                or action.recovery_warehouse_id not in facilities
                or action.vehicle_id not in vehicles
                or action.baseline_route_id not in routes
                or action.recovery_route_id not in routes
            ):
                raise ValueError(f"Logistics action {action.id} contains an invalid reference")
        for action in recovery.commerce_actions:
            if (
                action.order_id not in orders
                or action.store_id not in facilities
                or action.requested_product_id not in products
            ):
                raise ValueError(f"Commerce action {action.id} contains an invalid reference")
            if any(allocation.product_id not in products for allocation in action.allocations):
                raise ValueError(f"Commerce action {action.id} contains an invalid allocation")
