import pytest

from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.recovery import OrderOutcome, RecoveryConstraints
from app.schemas.simulation import InventoryOverride, RunSimulationRequest, VehicleOverride
from app.services.recovery_service import _logistics_action_type, generate_recovery_plan
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
        if action.action == "allocate":
            assert action.original_warehouse_id is None
            assert action.baseline_route_id is None
            assert action.baseline_eta_minutes is None
            assert action.baseline_flood_exposure is None
            continue
        assert action.baseline_route_id is not None
        baseline_route = baseline_routes[action.baseline_route_id]
        assert action.baseline_eta_minutes == baseline_route.eta_minutes
        assert action.baseline_flood_exposure == baseline_route.flood_exposure


def test_logistics_action_decision_matrix_uses_real_allocation_state_and_route_ids() -> None:
    def outcome(
        *,
        allocated: int,
        warehouse_id: str | None,
        route_id: str | None,
        eta_minutes: int | None = 16,
    ) -> OrderOutcome:
        return OrderOutcome(
            order_id="ORD-MATRIX",
            requested_quantity=10,
            allocated_quantity=allocated,
            allocated_value=float(allocated),
            warehouse_id=warehouse_id,
            vehicle_id="V-01" if allocated else None,
            route_id=route_id,
            eta_minutes=eta_minutes if allocated else None,
            deadline_minutes=30,
            delay_minutes=0,
            flood_exposure="low" if allocated else None,
        )

    baseline = outcome(allocated=10, warehouse_id="wh-west", route_id="route-baseline-west")
    same_assignment = outcome(allocated=10, warehouse_id="wh-west", route_id="route-baseline-west")
    equal_eta_reroute = outcome(allocated=10, warehouse_id="wh-west", route_id="route-recovery-west")
    warehouse_only = outcome(allocated=10, warehouse_id="wh-east", route_id="route-baseline-west")
    warehouse_and_route = outcome(allocated=10, warehouse_id="wh-east", route_id="route-recovery-east")
    unallocated = outcome(allocated=0, warehouse_id=None, route_id=None, eta_minutes=None)

    assert _logistics_action_type(baseline, same_assignment) is None
    assert _logistics_action_type(baseline, equal_eta_reroute) == "reroute"
    assert baseline.eta_minutes == equal_eta_reroute.eta_minutes
    assert _logistics_action_type(baseline, warehouse_only) == "reallocate"
    assert _logistics_action_type(baseline, warehouse_and_route) == "reallocate-reroute"
    assert _logistics_action_type(unallocated, equal_eta_reroute) == "allocate"


def test_new_allocation_does_not_expose_nominal_baseline_as_actual(simulation_id: str) -> None:
    scenario = get_historical_jakarta()
    disruption = simulation_repository.get_disruption(simulation_id)
    plan = generate_recovery_plan(simulation_id, scenario, disruption, RecoveryConstraints())

    action = next(item for item in plan.logistics_actions or [] if item.order_id == "ORD-012")
    before = next(item for item in plan.baseline_order_outcomes if item.order_id == "ORD-012")
    after = next(item for item in plan.recovery_order_outcomes if item.order_id == "ORD-012")

    assert before.allocated_quantity == 0
    assert before.warehouse_id is None and before.route_id is None and before.vehicle_id is None
    assert after.allocated_quantity > 0
    assert action.action == "allocate"
    assert action.action not in {"reallocate", "reallocate-reroute"}
    assert action.original_warehouse_id is None
    assert action.original_warehouse_name is None
    assert action.baseline_route_id is None
    assert action.baseline_eta_minutes is None
    assert action.baseline_flood_exposure is None


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


def test_custom_vehicle_is_authoritative_effective_capacity_and_changes_fingerprint(client) -> None:
    base_payload = {
        "scenarioId": "scenario-jakarta-20250304",
        "vehicleOverrides": [
            {"id": "V-01", "available": False},
            {"id": "V-02", "available": False},
            {"id": "V-03", "available": False},
        ],
    }
    without_custom = client.post("/api/simulations", json=base_payload)
    assert without_custom.status_code == 201
    without_id = without_custom.json()["id"]
    without_plan = client.post(f"/api/simulations/{without_id}/recovery", json={})
    assert without_plan.status_code == 201
    assert without_plan.json()["status"] == "no-feasible-plan"

    with_custom_payload = {
        **base_payload,
        "customVehicles": [
            {
                "id": "V-04",
                "label": "Armada Darurat",
                "capacityUnits": 5_000,
                "available": True,
            }
        ],
    }
    with_custom = client.post("/api/simulations", json=with_custom_payload)
    assert with_custom.status_code == 201
    with_id = with_custom.json()["id"]
    assert with_id != without_id

    effective = simulation_repository.get_effective_scenario(with_id)
    assert effective is not None
    assert len(effective.vehicles) == 4
    assert sum(vehicle.capacity_units for vehicle in effective.vehicles if vehicle.available) == 5_000
    assert next(vehicle for vehicle in effective.vehicles if vehicle.id == "V-04").label == "Armada Darurat"

    with_plan = client.post(f"/api/simulations/{with_id}/recovery", json={})
    assert with_plan.status_code == 201
    assert with_plan.json()["status"] in {"ready", "partial"}
    assert {action["vehicleId"] for action in with_plan.json()["logisticsActions"]} == {"V-04"}

    changed_capacity = client.post(
        "/api/simulations",
        json={
            **base_payload,
            "customVehicles": [
                {
                    "id": "V-04",
                    "label": "Armada Darurat",
                    "capacityUnits": 4_999,
                    "available": True,
                }
            ],
        },
    )
    assert changed_capacity.status_code == 201
    assert changed_capacity.json()["id"] != with_id


def test_inactive_custom_vehicle_provides_no_optimizer_capacity(client) -> None:
    response = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "vehicleOverrides": [
                {"id": "V-01", "available": False},
                {"id": "V-02", "available": False},
                {"id": "V-03", "available": False},
            ],
            "customVehicles": [
                {
                    "id": "V-04",
                    "label": "Armada Nonaktif",
                    "capacityUnits": 5_000,
                    "available": False,
                }
            ],
        },
    )
    assert response.status_code == 201
    simulation_id = response.json()["id"]
    effective = simulation_repository.get_effective_scenario(simulation_id)
    assert effective is not None
    assert sum(vehicle.capacity_units for vehicle in effective.vehicles if vehicle.available) == 0

    plan = client.post(f"/api/simulations/{simulation_id}/recovery", json={})
    assert plan.status_code == 201
    assert plan.json()["status"] == "no-feasible-plan"
    assert plan.json()["logisticsActions"] == []


def test_custom_vehicle_duplicate_and_invalid_capacity_are_rejected(client) -> None:
    duplicate = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "customVehicles": [
                {
                    "id": "V-01",
                    "label": "Duplikat",
                    "capacityUnits": 500,
                    "available": True,
                }
            ],
        },
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "DUPLICATE_VEHICLE_ID"
    assert duplicate.json()["details"] == {"vehicleId": "V-01"}

    invalid = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "customVehicles": [
                {
                    "id": "V-04",
                    "label": "Kapasitas Salah",
                    "capacityUnits": 0,
                    "available": True,
                }
            ],
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"


def test_existing_fleet_overrides_remain_authoritative(client) -> None:
    response = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "vehicleOverrides": [
                {"id": "V-01", "capacityUnits": 321},
                {"id": "V-02", "available": False},
                {"id": "V-03", "capacityUnits": 451, "available": True},
            ],
        },
    )
    assert response.status_code == 201
    effective = simulation_repository.get_effective_scenario(response.json()["id"])
    assert effective is not None
    vehicles = {vehicle.id: vehicle for vehicle in effective.vehicles}
    assert vehicles["V-01"].capacity_units == 321
    assert vehicles["V-02"].available is False
    assert vehicles["V-03"].capacity_units == 451
    assert vehicles["V-03"].available is True


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


def test_default_manufacturing_explanation_uses_plan_level_evidence(simulation_id: str) -> None:
    scenario = get_historical_jakarta().model_copy(deep=True)
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        simulation_repository.get_disruption(simulation_id),
        RecoveryConstraints(),
    )
    quantities = {
        action.product_id: (action.baseline_quantity, action.recovery_quantity)
        for action in plan.manufacturing_actions or []
    }

    assert quantities == {"prod-a": (240, 320), "prod-b": (260, 180)}
    assert plan.manufacturing_explanation is not None
    reason = plan.manufacturing_explanation.reason
    assert "Produk A" in reason and "Produk B" in reason
    assert "kapasitas pabrik 500 unit" in reason
    assert "bahan baku" not in reason.lower()
    assert "BOM" not in reason
    assert plan.manufacturing_explanation.expected_impact.endswith("18/20 menjadi 20/20.")
    assert next(action for action in plan.manufacturing_actions or [] if action.product_id == "prod-a").what == (
        "Naikkan produksi Produk A dari 240 menjadi 320 unit."
    )
    assert next(action for action in plan.manufacturing_actions or [] if action.product_id == "prod-b").what == (
        "Kurangi produksi Produk B dari 260 menjadi 180 unit."
    )


def test_material_binding_is_named_only_when_consumption_reaches_availability(simulation_id: str) -> None:
    scenario = get_historical_jakarta().model_copy(deep=True)
    next(material for material in scenario.materials if material.id == "mat-a").available_quantity = 250
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        simulation_repository.get_disruption(simulation_id),
        RecoveryConstraints(),
    )
    action = next(action for action in plan.manufacturing_actions or [] if action.product_id == "prod-a")

    assert action.recovery_quantity == 250
    assert plan.manufacturing_explanation is not None
    assert "bahan baku berdasarkan komposisi produk" in plan.manufacturing_explanation.reason.lower()
    assert "batas ketersediaan Bahan Utama A" in plan.manufacturing_explanation.reason


def test_bom_binding_is_grounded_in_computed_material_consumption(simulation_id: str) -> None:
    scenario = get_historical_jakarta().model_copy(deep=True)
    product = next(product for product in scenario.products if product.id == "prod-a")
    next(item for item in product.bom if item.material_id == "mat-a").quantity_per_unit = 2.0
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        simulation_repository.get_disruption(simulation_id),
        RecoveryConstraints(),
    )
    action = next(action for action in plan.manufacturing_actions or [] if action.product_id == "prod-a")

    assert action.recovery_quantity == 300
    assert action.recovery_quantity * 2 == 600
    assert plan.manufacturing_explanation is not None
    assert "komposisi produk" in plan.manufacturing_explanation.reason
    assert "batas ketersediaan Bahan Utama A" in plan.manufacturing_explanation.reason


def test_inventory_increase_does_not_retain_false_material_limitation(simulation_id: str) -> None:
    scenario = get_historical_jakarta().model_copy(deep=True)
    inventory = next(
        item for item in scenario.inventory if item.facility_id == "wh-west" and item.product_id == "prod-a"
    )
    inventory.quantity = 610
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        simulation_repository.get_disruption(simulation_id),
        RecoveryConstraints(),
    )
    action = next(action for action in plan.manufacturing_actions or [] if action.product_id == "prod-a")

    assert (action.baseline_quantity, action.recovery_quantity) == (20, 20)
    assert action.what == "Pertahankan produksi Produk A sebesar 20 unit."
    assert plan.manufacturing_explanation is not None
    assert "inventory" in plan.manufacturing_explanation.reason
    assert "mencapai batas ketersediaan" not in plan.manufacturing_explanation.reason
    assert "BOM" not in plan.manufacturing_explanation.reason
