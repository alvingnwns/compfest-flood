"""Independent re-verification of a solver plan against the source workbook and the network.

Nothing here imports solver code: every rule is recomputed from the uploaded workbook rows,
the published network (scenario + disruption routes) and the plan outcomes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from eval.workbook import BusinessData

PlanKind = Literal["baseline", "recovery"]


@dataclass
class Network:
    vehicles: dict[str, dict[str, Any]]
    preferred_warehouse: dict[str, str]
    factory_capacity: int
    routes: dict[str, dict[str, Any]]


@dataclass
class CheckReport:
    checks: int = 0
    violations: list[dict[str, Any]] = field(default_factory=list)
    checks_by_rule: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def expect(self, ok: bool, rule: str, **detail: Any) -> None:
        self.checks += 1
        self.checks_by_rule[rule] += 1
        if not ok:
            self.violations.append({"rule": rule, **detail})

    def as_dict(self) -> dict[str, Any]:
        return {
            "checks": self.checks,
            "violations": len(self.violations),
            "checks_by_rule": dict(self.checks_by_rule),
            "violation_details": self.violations,
        }


def check_plan(
    *,
    plan: PlanKind,
    data: BusinessData,
    network: Network,
    outcomes: list[dict[str, Any]],
    production: dict[str, int],
    allocations: dict[str, list[tuple[str, int]]] | None,
    allow_substitution: bool,
) -> CheckReport:
    """Check one plan. `allocations` maps order -> [(productId, qty)]; None means requested product only."""
    report = CheckReport()
    if not outcomes:
        return report

    orders = {row["orderId"]: row for row in data["Orders"]}
    inventory: dict[tuple[str, str], int] = defaultdict(int)
    for row in data["Inventory"]:
        inventory[row["warehouseId"], row["productId"]] += round(float(row["availableQuantity"]))
    by_order = {outcome["order_id"]: outcome for outcome in outcomes}

    for order_id in orders:
        report.expect(order_id in by_order, "order-coverage", plan=plan, order_id=order_id)

    allocated_by_warehouse_product: dict[tuple[str, str], int] = defaultdict(int)
    load_by_vehicle: dict[str, int] = defaultdict(int)

    for order_id, outcome in by_order.items():
        order = orders.get(order_id)
        report.expect(order is not None, "order-known", plan=plan, order_id=order_id)
        if order is None:
            continue
        requested = int(order["quantity"])
        allocated = int(outcome["allocated_quantity"])

        report.expect(
            int(outcome["requested_quantity"]) == requested,
            "requested-matches-source",
            plan=plan,
            order_id=order_id,
            source=requested,
            reported=outcome["requested_quantity"],
        )
        report.expect(
            0 <= allocated <= requested,
            "allocated-within-requested",
            plan=plan,
            order_id=order_id,
            allocated=allocated,
            requested=requested,
        )
        if order["priority"] == "critical":
            report.expect(
                allocated == requested,
                "critical-fully-allocated",
                plan=plan,
                order_id=order_id,
                allocated=allocated,
                requested=requested,
            )
        if allocated == 0:
            continue

        warehouse_id = outcome["warehouse_id"]
        vehicle_id = outcome["vehicle_id"]
        route_id = outcome["route_id"]
        report.expect(
            bool(warehouse_id and vehicle_id and route_id),
            "assignment-complete",
            plan=plan,
            order_id=order_id,
            warehouse_id=warehouse_id,
            vehicle_id=vehicle_id,
            route_id=route_id,
        )

        lines = allocations.get(order_id, []) if allocations is not None else [(order["productId"], allocated)]
        line_total = sum(quantity for _, quantity in lines)
        report.expect(
            line_total == allocated,
            "allocation-lines-sum",
            plan=plan,
            order_id=order_id,
            line_total=line_total,
            allocated=allocated,
        )
        for product_id, quantity in lines:
            substituted = product_id != order["productId"]
            report.expect(
                not substituted or allow_substitution,
                "substitution-allowed",
                plan=plan,
                order_id=order_id,
                requested_product=order["productId"],
                allocated_product=product_id,
                allow_substitution=allow_substitution,
            )
            if warehouse_id:
                allocated_by_warehouse_product[warehouse_id, product_id] += quantity

        if vehicle_id:
            vehicle = network.vehicles.get(vehicle_id)
            report.expect(
                vehicle is not None and bool(vehicle["available"]),
                "vehicle-available",
                plan=plan,
                order_id=order_id,
                vehicle_id=vehicle_id,
            )
            load_by_vehicle[vehicle_id] += allocated

        if plan == "baseline":
            preferred = network.preferred_warehouse.get(order["storeId"])
            report.expect(
                warehouse_id == preferred,
                "baseline-preferred-warehouse",
                plan=plan,
                order_id=order_id,
                warehouse_id=warehouse_id,
                preferred_warehouse_id=preferred,
            )

        if route_id:
            route = network.routes.get(route_id)
            report.expect(route is not None, "route-known", plan=plan, order_id=order_id, route_id=route_id)
            if route is not None:
                report.expect(
                    route["origin"] == warehouse_id and route["destination"] == order["storeId"],
                    "route-matches-order",
                    plan=plan,
                    order_id=order_id,
                    route_id=route_id,
                    route_origin=route["origin"],
                    route_destination=route["destination"],
                    warehouse_id=warehouse_id,
                    store_id=order["storeId"],
                )
                if plan == "recovery":
                    report.expect(
                        route["flood_exposure"] != "critical",
                        "no-critical-route",
                        plan=plan,
                        order_id=order_id,
                        route_id=route_id,
                        flood_exposure=route["flood_exposure"],
                    )

    for vehicle_id, load in sorted(load_by_vehicle.items()):
        capacity = network.vehicles.get(vehicle_id, {}).get("capacity", 0)
        report.expect(
            load <= capacity,
            "vehicle-capacity",
            plan=plan,
            vehicle_id=vehicle_id,
            load=load,
            capacity=capacity,
        )

    # Production-to-warehouse delivery is not published, so check the exact feasibility
    # condition: warehouse shortfalls for a product must be coverable by that product's output.
    products = {product_id for _, product_id in allocated_by_warehouse_product} | set(production)
    for product_id in sorted(products):
        shortfall = {
            warehouse_id: allocated - inventory.get((warehouse_id, product_id), 0)
            for (warehouse_id, pid), allocated in allocated_by_warehouse_product.items()
            if pid == product_id and allocated > inventory.get((warehouse_id, product_id), 0)
        }
        produced = int(production.get(product_id, 0))
        report.expect(
            produced >= 0 and sum(shortfall.values()) <= produced,
            "warehouse-inventory",
            plan=plan,
            product_id=product_id,
            shortfall_by_warehouse=shortfall,
            produced=produced,
        )

    total_production = sum(int(quantity) for quantity in production.values())
    report.expect(
        total_production <= network.factory_capacity,
        "factory-capacity",
        plan=plan,
        total_production=total_production,
        capacity=network.factory_capacity,
    )
    return report
