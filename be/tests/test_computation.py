from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.recovery import RecoveryConstraints
from app.services.recovery_service import generate_recovery_plan


def test_risk_changes_networkx_route(simulation_id: str) -> None:
    disruption = simulation_repository.get_disruption(simulation_id)
    baseline = next(route for route in disruption.routes if route.id == "route-baseline-wh-east-store-d")
    recovery = next(route for route in disruption.routes if route.id == "route-recovery-wh-east-store-d")
    assert baseline.affected_road_segment_ids != recovery.affected_road_segment_ids
    assert recovery.flood_exposure_probability < baseline.flood_exposure_probability


def test_business_outputs_are_computed_and_referentially_valid(simulation_id: str) -> None:
    scenario = get_historical_jakarta()
    disruption = simulation_repository.get_disruption(simulation_id)
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=30),
    )
    products = {product.id for product in scenario.products}
    orders = {order.id for order in scenario.orders}
    vehicles = {vehicle.id for vehicle in scenario.vehicles if vehicle.available}
    route_ids = {route.id for route in disruption.routes}
    assert plan.status in {"ready", "partial"}
    assert plan.manufacturing_actions
    assert any(action.baseline_quantity != action.recovery_quantity for action in plan.manufacturing_actions)
    assert {action.product_id for action in plan.manufacturing_actions} <= products
    assert {action.order_id for action in plan.commerce_actions or []} == orders
    assert {action.vehicle_id for action in plan.logistics_actions or []} <= vehicles
    assert {action.recovery_route_id for action in plan.logistics_actions or []} <= route_ids


def test_maximum_additional_delay_changes_feasibility(simulation_id: str) -> None:
    scenario = get_historical_jakarta()
    disruption = simulation_repository.get_disruption(simulation_id)
    strict = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=0),
    )
    flexible = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=30),
    )
    assert strict.status == "no-feasible-plan"
    assert flexible.status in {"ready", "partial"}


def test_no_feasible_when_material_inventory_and_substitution_are_unavailable(simulation_id: str) -> None:
    scenario = get_historical_jakarta().model_copy(deep=True)
    for material in scenario.materials:
        material.available_quantity = 0
    for inventory in scenario.inventory:
        inventory.quantity = 0
    disruption = simulation_repository.get_disruption(simulation_id)
    result = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        RecoveryConstraints(allow_substitution=False, max_additional_delay_minutes=30),
    )
    payload = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert result.status == "no-feasible-plan"
    assert payload["completedAt"]
    assert payload["summary"]["recoverableOrders"] == 0
    assert payload["error"]["code"] == "no_feasible_plan"
    assert payload["manufacturingActions"] == []


def test_kpis_equal_actual_order_outcomes(client, simulation_id: str) -> None:
    client.post(
        f"/api/simulations/{simulation_id}/recovery",
        json={"constraints": {"allowSubstitution": True, "maxAdditionalDelayMinutes": 30}},
    )
    recovery = simulation_repository.get_recovery(simulation_id)
    impact = client.get(f"/api/simulations/{simulation_id}/impact").json()
    metrics = {metric["key"]: metric for metric in impact["metrics"]}
    outcomes = recovery.recovery_order_outcomes
    assert metrics["orders-fulfilled"]["recovery"] == sum(
        item.allocated_quantity == item.requested_quantity for item in outcomes
    )
    assert metrics["failed-orders"]["recovery"] == sum(item.allocated_quantity == 0 for item in outcomes)
    assert metrics["on-time-delivery"]["recovery"] == sum(
        item.allocated_quantity == item.requested_quantity and item.delay_minutes == 0 for item in outcomes
    ) / len(outcomes)
    expected_delay = sum(item.delay_minutes for item in outcomes if item.allocated_quantity > 0) / sum(
        item.allocated_quantity > 0 for item in outcomes
    )
    assert metrics["average-delay"]["recovery"] == expected_delay
    scenario = get_historical_jakarta()
    prices = {product.id: product.unit_price for product in scenario.products}
    order_products = {order.id: order.product_id for order in scenario.orders}
    expected_exposure = sum(
        (item.requested_quantity - item.allocated_quantity) * prices[order_products[item.order_id]] for item in outcomes
    )
    assert metrics["sales-exposure-risk"]["recovery"] == expected_exposure
