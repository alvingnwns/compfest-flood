from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.recovery import RecoveryConstraints
from app.schemas.simulation import InventoryOverride, RunSimulationRequest, VehicleOverride
from app.services.recovery_service import generate_recovery_plan
from app.services.routing_service import calculate_routes
from app.services.simulation_service import _apply_overrides


def test_risk_changes_networkx_route(simulation_id: str) -> None:
    normal_route = calculate_routes("wh-east", "store-d", {})[0]
    routes = []
    for segment_id in normal_route.affected_road_segment_ids:
        candidate = calculate_routes(
            "wh-east",
            "store-d",
            {segment_id: {"riskLevel": "critical", "riskProbability": 0.99}},
        )
        if any(route.type == "recovery" for route in candidate):
            routes = candidate
            break
    assert routes, "The processed OSM corridor must retain at least one risk-sensitive alternative."
    baseline = next(route for route in routes if route.type == "baseline")
    recovery = next(route for route in routes if route.type == "recovery")
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
    baseline_routes = {route.id: route for route in disruption.routes if route.type == "baseline"}
    for action in plan.logistics_actions or []:
        baseline_route = baseline_routes[action.baseline_route_id]
        assert action.baseline_eta_minutes == baseline_route.eta_minutes
        assert action.baseline_flood_exposure == baseline_route.flood_exposure


def test_maximum_additional_delay_changes_feasibility(simulation_id: str) -> None:
    scenario = get_historical_jakarta()
    disruption = simulation_repository.get_disruption(simulation_id)
    recovery_routes = [
        route.model_copy(
            update={
                "id": route.id.replace("route-baseline", "route-recovery"),
                "type": "recovery",
                "eta_minutes": route.eta_minutes + 10,
            }
        )
        for route in disruption.routes
        if route.type == "baseline"
    ]
    delayed_disruption = disruption.model_copy(update={"routes": [*disruption.routes, *recovery_routes]})
    strict = generate_recovery_plan(
        simulation_id,
        scenario,
        delayed_disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=0),
    )
    flexible = generate_recovery_plan(
        simulation_id,
        scenario,
        delayed_disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=10),
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


# --- Operational override tests ---


def test_vehicle_override_disables_vehicle() -> None:
    """Disabling a vehicle via override removes it from the available fleet."""
    scenario = get_historical_jakarta()
    available_before = [v.id for v in scenario.vehicles if v.available]
    assert len(available_before) > 1, "Need at least 2 available vehicles for this test"

    target_id = available_before[0]
    request = RunSimulationRequest(
        scenario_id=scenario.id,
        vehicle_overrides=[VehicleOverride(id=target_id, available=False)],
    )
    effective = _apply_overrides(scenario, request)
    available_after = [v.id for v in effective.vehicles if v.available]
    assert target_id not in available_after
    assert len(available_after) == len(available_before) - 1


def test_vehicle_override_reduces_capacity() -> None:
    """Reducing vehicle capacity via override is reflected in the effective scenario."""
    scenario = get_historical_jakarta()
    available = [v for v in scenario.vehicles if v.available]
    assert available, "Need at least one available vehicle"
    target = available[0]
    reduced = max(1, target.capacity_units // 2)

    request = RunSimulationRequest(
        scenario_id=scenario.id,
        vehicle_overrides=[VehicleOverride(id=target.id, capacity_units=reduced)],
    )
    effective = _apply_overrides(scenario, request)
    overridden = next(v for v in effective.vehicles if v.id == target.id)
    assert overridden.capacity_units == reduced
    assert overridden.available == target.available


def test_inventory_override_changes_quantity() -> None:
    """Inventory override changes the effective stock without affecting original scenario."""
    scenario = get_historical_jakarta()
    assert scenario.inventory, "Scenario must have inventory entries"
    first = scenario.inventory[0]
    new_qty = max(0.0, first.quantity / 2)

    request = RunSimulationRequest(
        scenario_id=scenario.id,
        inventory_overrides=[
            InventoryOverride(facility_id=first.facility_id, product_id=first.product_id, quantity=new_qty)
        ],
    )
    effective = _apply_overrides(scenario, request)
    overridden = next(
        item
        for item in effective.inventory
        if item.facility_id == first.facility_id and item.product_id == first.product_id
    )
    assert overridden.quantity == new_qty
    # Original scenario must be unchanged (cached singleton not mutated)
    original = next(
        item
        for item in scenario.inventory
        if item.facility_id == first.facility_id and item.product_id == first.product_id
    )
    assert original.quantity == first.quantity


def test_vehicle_override_creates_distinct_simulation(client) -> None:
    """Two simulation requests with different vehicle overrides must create distinct IDs."""
    payload_default = {"scenarioId": "scenario-jakarta-20250304"}
    payload_override = {
        "scenarioId": "scenario-jakarta-20250304",
        "vehicleOverrides": [{"id": get_historical_jakarta().vehicles[0].id, "available": False}],
    }
    default_sim = client.post("/api/simulations", json=payload_default)
    override_sim = client.post("/api/simulations", json=payload_override)
    assert default_sim.status_code == 201
    assert override_sim.status_code == 201
    assert default_sim.json()["id"] != override_sim.json()["id"]


def test_road_context_endpoint_returns_geojson(client) -> None:
    """The road context endpoint must return GeoJSON with display-only features."""
    import pytest

    pytest.importorskip("app.repositories.geospatial_repository")
    from pathlib import Path

    context_path = Path(__file__).resolve().parents[1] / "app" / "data" / "roads" / "jakarta-road-context.geojson"
    if not context_path.exists():
        pytest.skip("Road context file not yet generated — run scripts/prepare_road_context.py")
    response = client.get("/api/map/road-context")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 100
    assert data["metadata"]["runtimeExternalDependency"] is None
    assert "display" in data["metadata"]["description"].lower()


def test_operational_overrides_propagate_to_recovery(client) -> None:
    resp_a = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert resp_a.status_code == 201
    sim_a_id = resp_a.json()["id"]
    rec_a = client.post(f"/api/simulations/{sim_a_id}/recovery", json={}).json()

    resp_b = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "vehicleOverrides": [{"id": "V-03", "available": False}],
        },
    )
    assert resp_b.status_code == 201
    sim_b_id = resp_b.json()["id"]
    assert sim_b_id != sim_a_id
    rec_b = client.post(f"/api/simulations/{sim_b_id}/recovery", json={}).json()

    vehicles_a = {action["vehicleId"] for action in rec_a["logisticsActions"]}
    vehicles_b = {action["vehicleId"] for action in rec_b["logisticsActions"]}

    assert "V-03" in vehicles_a
    assert "V-03" not in vehicles_b


def test_critical_stock_preset_causes_computed_solver_shift(client) -> None:
    """Critical stock preset overriding both warehouses causes real computed production and allocation shifts."""
    resp_norm = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert resp_norm.status_code == 201
    sim_norm_id = resp_norm.json()["id"]
    client.post(f"/api/simulations/{sim_norm_id}/recovery", json={})
    rec_norm = simulation_repository.get_recovery(sim_norm_id)

    resp_crit = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "inventoryOverrides": [
                {"facilityId": "wh-east", "productId": "prod-a", "quantity": 50},
                {"facilityId": "wh-west", "productId": "prod-a", "quantity": 50},
            ],
        },
    )
    assert resp_crit.status_code == 201
    sim_crit_id = resp_crit.json()["id"]
    client.post(f"/api/simulations/{sim_crit_id}/recovery", json={})
    rec_crit = simulation_repository.get_recovery(sim_crit_id)

    assert rec_norm is not None and rec_crit is not None
    prod_norm = {p.product_id: p.quantity for p in rec_norm.recovery_production}
    prod_crit = {p.product_id: p.quantity for p in rec_crit.recovery_production}

    # Verify real computed production shift: Product A production increases from 320 to 450
    assert prod_crit["prod-a"] > prod_norm["prod-a"]
    assert prod_crit["prod-b"] < prod_norm["prod-b"]
