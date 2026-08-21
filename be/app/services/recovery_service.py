from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from ortools.sat.python import cp_model

from app.core.config import get_settings
from app.schemas.common import ErrorResponse
from app.schemas.disruption import DisruptionAnalysis, Route
from app.schemas.recovery import (
    CommerceAction,
    CommerceAllocation,
    LogisticsAction,
    ManufacturingAction,
    OrderOutcome,
    ProductionOutcome,
    RecoveryConstraints,
    RecoveryResult,
    RecoverySummary,
)
from app.schemas.scenario import Scenario

RISK_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
BOM_SCALE = 10


@dataclass
class ComputedPlan:
    feasible: bool
    production: dict[str, int]
    outcomes: list[OrderOutcome]
    allocations: dict[str, list[tuple[str, int]]]


def generate_recovery_plan(
    simulation_id: str,
    scenario: Scenario,
    disruption: DisruptionAnalysis,
    constraints: RecoveryConstraints | None,
) -> RecoveryResult:
    baseline = _solve_plan(scenario, disruption, RecoveryConstraints(), baseline=True)
    recovery = _solve_plan(scenario, disruption, constraints or RecoveryConstraints(), baseline=False)
    now = datetime.now(UTC)
    if not recovery.feasible:
        return RecoveryResult(
            id=f"plan-{uuid.uuid4().hex[:8]}",
            simulation_id=simulation_id,
            status="no-feasible-plan",
            created_at=now,
            completed_at=now,
            summary=RecoverySummary(
                risks_mitigated=0,
                operational_changes=0,
                recoverable_orders=0,
                total_orders=len(scenario.orders),
            ),
            manufacturing_actions=[],
            logistics_actions=[],
            commerce_actions=[],
            possible_next_actions=[
                "Pulihkan ketersediaan bahan baku atau persediaan gudang untuk pesanan prioritas.",
                "Izinkan rute aman atau longgarkan kendala batas keterlambatan waktu.",
            ],
            error=ErrorResponse(
                code="no_feasible_plan",
                message=(
                    "Permintaan pesanan kritis tidak dapat dipenuhi berdasarkan kendala operasional yang diberikan."
                ),
                retryable=False,
                details={"criticalOrderPolicy": "semua permintaan pesanan kritis harus dialokasikan"},
            ),
            baseline_order_outcomes=baseline.outcomes,
            baseline_production=_production_outcomes(baseline.production),
        )

    baseline_by_order = {outcome.order_id: outcome for outcome in baseline.outcomes}
    recovery_by_order = {outcome.order_id: outcome for outcome in recovery.outcomes}
    baseline_routes = {
        (route.origin_facility_id, route.destination_facility_id): route
        for route in disruption.routes
        if route.type == "baseline"
    }
    products = {product.id: product for product in scenario.products}
    stores = {facility.id: facility for facility in scenario.facilities if facility.kind == "store"}
    warehouses = {facility.id: facility for facility in scenario.facilities if facility.kind == "warehouse"}

    manufacturing = []
    for product in scenario.products:
        before = baseline.production.get(product.id, 0)
        after = recovery.production.get(product.id, 0)
        change = after - before
        if before == 0 and after == 0:
            continue
        constrained_materials = ", ".join(item.material_id for item in product.bom)
        if change != 0:
            what = f"Sesuaikan produksi {product.name} dari {before} menjadi {after} {product.unit}."
            why = (
                f"Ketersediaan bahan baku dan kebutuhan BOM ({constrained_materials}) membatasi kapasitas produksi."
            )
            expected_impact = (
                "Penyesuaian produksi menyediakan persediaan yang dapat dialokasikan untuk pemenuhan pesanan."
            )
        else:
            what = f"Pertahankan produksi {product.name} sebesar {after} {product.unit}."
            why = (
                f"Alokasi kapasitas pabrik untuk {product.name} dipertahankan guna memenuhi kebutuhan pesanan dan ketersediaan bahan ({constrained_materials})."
            )
            expected_impact = (
                f"Menjaga ketersediaan {after} {product.unit} persediaan untuk pemenuhan pesanan prioritas."
            )

        manufacturing.append(
            ManufacturingAction(
                id=f"mfg-{product.id}",
                product_id=product.id,
                product_name=product.name,
                baseline_quantity=before,
                recovery_quantity=after,
                change_quantity=change,
                what=what,
                why=why,
                expected_impact=expected_impact,
            )
        )

    logistics = []
    risks_mitigated = 0
    for order in scenario.orders:
        before = baseline_by_order.get(order.id)
        after = recovery_by_order.get(order.id)
        baseline_route = baseline_routes.get((order.preferred_warehouse_id, order.store_id))
        if not before or not after or not after.warehouse_id or not after.route_id or not after.vehicle_id:
            continue
        warehouse_changed = before.warehouse_id != after.warehouse_id
        route_changed = before.route_id != after.route_id
        if not warehouse_changed and not route_changed:
            continue
        if before.flood_exposure and after.flood_exposure:
            risks_mitigated += int(RISK_RANK[after.flood_exposure] < RISK_RANK[before.flood_exposure])
        action = (
            "reallocate-reroute"
            if warehouse_changed and route_changed
            else "reallocate"
            if warehouse_changed
            else "reroute"
        )
        logistics.append(
            LogisticsAction(
                id=f"log-{order.id}",
                order_id=order.id,
                original_warehouse_id=before.warehouse_id or order.preferred_warehouse_id,
                original_warehouse_name=warehouses[before.warehouse_id or order.preferred_warehouse_id].name,
                recovery_warehouse_id=after.warehouse_id,
                recovery_warehouse_name=warehouses[after.warehouse_id].name,
                vehicle_id=after.vehicle_id,
                baseline_route_id=before.route_id or (baseline_route.id if baseline_route else after.route_id),
                recovery_route_id=after.route_id,
                baseline_eta_minutes=before.eta_minutes or (baseline_route.eta_minutes if baseline_route else 0),
                recovery_eta_minutes=after.eta_minutes or 0,
                baseline_flood_exposure=before.flood_exposure
                or (baseline_route.flood_exposure if baseline_route else "low"),
                recovery_flood_exposure=after.flood_exposure or "low",
                action=action,
                what=(
                    f"Gunakan {warehouses[after.warehouse_id].name} dan kendaraan {after.vehicle_id} untuk {order.id}."
                ),
                why="Alokasi CP-SAT memilih rute dan kendaraan yang layak dalam batas kapasitas dan keterlambatan.",
                expected_impact=(
                    f"Waktu tempuh {after.eta_minutes} menit dengan tingkat paparan banjir {after.flood_exposure}."
                ),
            )
        )

    commerce = []
    for order in scenario.orders:
        outcome = recovery_by_order[order.id]
        allocations = recovery.allocations.get(order.id, [])
        has_substitute = any(product_id != order.product_id for product_id, _ in allocations)
        if outcome.allocated_quantity == 0:
            action = "delay"
        elif outcome.allocated_quantity < order.quantity and has_substitute:
            action = "split-substitute"
        elif outcome.allocated_quantity < order.quantity:
            action = "split"
        elif has_substitute:
            action = "substitute"
        elif order.priority == "critical":
            action = "prioritize"
        else:
            action = "fulfill"
        commerce.append(
            CommerceAction(
                id=f"com-{order.id}",
                order_id=order.id,
                store_id=order.store_id,
                store_name=stores[order.store_id].name,
                requested_product_id=order.product_id,
                requested_product_name=products[order.product_id].name,
                requested_quantity=order.quantity,
                action=action,
                allocations=[
                    CommerceAllocation(
                        product_id=product_id,
                        product_name=products[product_id].name,
                        quantity=quantity,
                    )
                    for product_id, quantity in allocations
                ],
                what=f"Penuhi pesanan {order.id} sebanyak {outcome.allocated_quantity}/{order.quantity} unit.",
                why=(
                    "Hasil alokasi memenuhi kendala persediaan, kapasitas produksi, substitusi produk, rute,"
                    " kendaraan, dan batas waktu."
                ),
                expected_impact=(
                    f"Perkiraan keterlambatan {outcome.delay_minutes} menit; nilai penjualan terlindungi sebesar IDR"
                    f" {outcome.allocated_value:.0f}."
                ),
            )
        )

    recoverable = sum(outcome.allocated_quantity == outcome.requested_quantity for outcome in recovery.outcomes)
    changed_commerce = sum(action.action not in {"fulfill", "prioritize"} for action in commerce)
    return RecoveryResult(
        id=f"plan-{uuid.uuid4().hex[:8]}",
        simulation_id=simulation_id,
        status="ready" if recoverable == len(scenario.orders) else "partial",
        created_at=now,
        completed_at=now,
        summary=RecoverySummary(
            risks_mitigated=risks_mitigated,
            operational_changes=len(manufacturing) + len(logistics) + changed_commerce,
            recoverable_orders=recoverable,
            total_orders=len(scenario.orders),
        ),
        manufacturing_actions=manufacturing,
        logistics_actions=logistics,
        commerce_actions=commerce,
        possible_next_actions=["Restore disrupted inbound material capacity.", "Review delayed non-critical orders."],
        baseline_order_outcomes=baseline.outcomes,
        recovery_order_outcomes=recovery.outcomes,
        baseline_production=_production_outcomes(baseline.production),
        recovery_production=_production_outcomes(recovery.production),
    )


def _production_outcomes(production: dict[str, int]) -> list[ProductionOutcome]:
    return [ProductionOutcome(product_id=product_id, quantity=quantity) for product_id, quantity in production.items()]


def _solve_plan(
    scenario: Scenario,
    disruption: DisruptionAnalysis,
    constraints: RecoveryConstraints,
    *,
    baseline: bool,
) -> ComputedPlan:
    settings = get_settings()
    priority_reward = {
        "normal": settings.objective_reward_normal,
        "high": settings.objective_reward_high,
        "critical": settings.objective_reward_critical,
    }
    model = cp_model.CpModel()
    products = {product.id: product for product in scenario.products}
    warehouses = [facility for facility in scenario.facilities if facility.kind == "warehouse"]
    vehicles = [vehicle for vehicle in scenario.vehicles if vehicle.available]
    factory_capacity = sum(
        facility.production_capacity_units or 0 for facility in scenario.facilities if facility.kind == "factory"
    )
    route_index = {
        (route.origin_facility_id, route.destination_facility_id, route.type): route for route in disruption.routes
    }
    material_available = _material_availability(scenario, disruption, baseline=baseline)

    production = {
        product.id: model.new_int_var(0, factory_capacity, f"produce_{product.id}") for product in scenario.products
    }
    delivered = {
        (product.id, warehouse.id): model.new_int_var(0, factory_capacity, f"deliver_{product.id}_{warehouse.id}")
        for product in scenario.products
        for warehouse in warehouses
    }
    for product in scenario.products:
        model.add(sum(delivered[product.id, warehouse.id] for warehouse in warehouses) == production[product.id])
    model.add(sum(production.values()) <= factory_capacity)
    for material in scenario.materials:
        consumption = []
        for product in scenario.products:
            bom = next((item for item in product.bom if item.material_id == material.id), None)
            if bom:
                consumption.append(production[product.id] * round(bom.quantity_per_unit * BOM_SCALE))
        if consumption:
            model.add(sum(consumption) <= round(material_available[material.id] * BOM_SCALE))

    route_options: dict[tuple[str, str], Route] = {}
    for order in scenario.orders:
        baseline_reference = route_index.get((order.preferred_warehouse_id, order.store_id, "baseline"))
        for warehouse in warehouses:
            normal = route_index.get((warehouse.id, order.store_id, "baseline"))
            safer = route_index.get((warehouse.id, order.store_id, "recovery"))
            selected = normal if baseline else safer or normal
            if selected is None:
                continue
            if not baseline and selected.flood_exposure == "critical":
                continue
            if (
                not baseline
                and constraints.max_additional_delay_minutes is not None
                and baseline_reference
                and selected.eta_minutes - baseline_reference.eta_minutes > constraints.max_additional_delay_minutes
            ):
                continue
            if baseline and warehouse.id != order.preferred_warehouse_id:
                continue
            route_options[order.id, warehouse.id] = selected

    assignments = {}
    quantities = {}
    for order in scenario.orders:
        allowed_products = [order.product_id]
        if not baseline and constraints.allow_substitution:
            allowed_products.extend(products[order.product_id].substitute_product_ids)
        order_assignments = []
        for warehouse in warehouses:
            route = route_options.get((order.id, warehouse.id))
            if not route:
                continue
            for vehicle in vehicles:
                assign = model.new_bool_var(f"assign_{order.id}_{warehouse.id}_{vehicle.id}")
                assignments[order.id, warehouse.id, vehicle.id] = assign
                order_assignments.append(assign)
                for product_id in allowed_products:
                    quantity = model.new_int_var(
                        0, order.quantity, f"qty_{order.id}_{warehouse.id}_{vehicle.id}_{product_id}"
                    )
                    quantities[order.id, warehouse.id, vehicle.id, product_id] = quantity
                    model.add(quantity <= order.quantity * assign)
        model.add_at_most_one(order_assignments)
        order_quantities = [quantity for key, quantity in quantities.items() if key[0] == order.id]
        if order_assignments:
            model.add(sum(order_quantities) >= sum(order_assignments))
        model.add(sum(order_quantities) <= order.quantity)
        if order.priority == "critical":
            model.add(sum(order_quantities) == order.quantity)

    inventory = {(item.facility_id, item.product_id): round(item.quantity) for item in scenario.inventory}
    for warehouse in warehouses:
        for product in scenario.products:
            allocated = [
                quantity for key, quantity in quantities.items() if key[1] == warehouse.id and key[3] == product.id
            ]
            model.add(
                sum(allocated) <= inventory.get((warehouse.id, product.id), 0) + delivered[product.id, warehouse.id]
            )
    for vehicle in vehicles:
        model.add(
            sum(quantity for key, quantity in quantities.items() if key[2] == vehicle.id) <= vehicle.capacity_units
        )

    objective = []
    orders = {order.id: order for order in scenario.orders}
    for key, quantity in quantities.items():
        order_id, _, _, product_id = key
        substitution_penalty = (
            settings.objective_substitution_penalty if product_id != orders[order_id].product_id else 0
        )
        objective.append(quantity * (priority_reward[orders[order_id].priority] - substitution_penalty))
    for (order_id, warehouse_id, vehicle_id), assignment in assignments.items():
        route = route_options[order_id, warehouse_id]
        vehicle = next(item for item in vehicles if item.id == vehicle_id)
        delay = max(0, round(route.eta_minutes) - orders[order_id].deadline_minutes)
        risk_penalty = RISK_RANK[route.flood_exposure] * settings.objective_risk_penalty
        transport_penalty = round(route.distance_km * vehicle.cost_per_km / settings.objective_transport_cost_scale)
        objective.append(-assignment * (delay * settings.objective_delay_penalty + risk_penalty + transport_penalty))
    objective.extend(-variable * settings.objective_production_penalty for variable in production.values())
    model.maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    status = solver.solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return ComputedPlan(False, {}, [], {})

    produced = {product_id: solver.value(variable) for product_id, variable in production.items()}
    allocations: dict[str, list[tuple[str, int]]] = {}
    outcomes = []
    for order in scenario.orders:
        selected_warehouse = selected_vehicle = None
        selected_route = None
        for (order_id, warehouse_id, vehicle_id), assignment in assignments.items():
            if order_id == order.id and solver.value(assignment):
                selected_warehouse, selected_vehicle = warehouse_id, vehicle_id
                selected_route = route_options[order.id, warehouse_id]
                break
        order_allocations = []
        for key, variable in quantities.items():
            if key[0] == order.id and solver.value(variable) > 0:
                order_allocations.append((key[3], solver.value(variable)))
        allocations[order.id] = order_allocations
        allocated = sum(quantity for _, quantity in order_allocations)
        eta = round(selected_route.eta_minutes) if selected_route else None
        outcomes.append(
            OrderOutcome(
                order_id=order.id,
                requested_quantity=order.quantity,
                allocated_quantity=allocated,
                allocated_value=allocated * products[order.product_id].unit_price,
                warehouse_id=selected_warehouse,
                vehicle_id=selected_vehicle,
                route_id=selected_route.id if selected_route else None,
                eta_minutes=eta,
                deadline_minutes=order.deadline_minutes,
                delay_minutes=max(0, (eta or order.deadline_minutes) - order.deadline_minutes),
                flood_exposure=selected_route.flood_exposure if selected_route else None,
            )
        )
    return ComputedPlan(True, produced, outcomes, allocations)


def _material_availability(scenario: Scenario, disruption: DisruptionAnalysis, *, baseline: bool) -> dict[str, float]:
    if baseline:
        return {material.id: material.available_quantity for material in scenario.materials}
    settings = get_settings()
    factors = {
        "low": 1.0,
        "medium": settings.supplier_availability_medium,
        "high": settings.supplier_availability_high,
        "critical": settings.supplier_availability_critical,
    }
    supplier_risk = {material.supplier_id: "low" for material in scenario.materials}
    for route in disruption.routes:
        if route.type != "baseline" or route.origin_facility_id not in supplier_risk:
            continue
        if RISK_RANK[route.flood_exposure] > RISK_RANK[supplier_risk[route.origin_facility_id]]:
            supplier_risk[route.origin_facility_id] = route.flood_exposure
    return {
        material.id: material.available_quantity * factors[supplier_risk[material.supplier_id]]
        for material in scenario.materials
    }
