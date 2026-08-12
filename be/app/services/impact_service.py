from __future__ import annotations

from app.schemas.common import Money
from app.schemas.disruption import OperationalImpact, PrioritizedIssue, RoadRisk, Route
from app.schemas.scenario import Scenario


def calculate_impact(scenario: Scenario, road_risks: list[RoadRisk], routes: list[Route]) -> OperationalImpact:
    risky_segments = {road.segment_id for road in road_risks if road.risk_level in {"high", "critical"}}
    impacted_suppliers: set[str] = set()
    impacted_warehouses: set[str] = set()
    impacted_stores: set[str] = set()
    issues: list[PrioritizedIssue] = []
    facility_kind = {facility.id: facility.kind for facility in scenario.facilities}
    for route in routes:
        if route.type != "baseline" or not risky_segments.intersection(route.affected_road_segment_ids):
            continue
        for facility_id in (route.origin_facility_id, route.destination_facility_id):
            kind = facility_kind.get(facility_id)
            if kind == "supplier":
                impacted_suppliers.add(facility_id)
            elif kind == "warehouse":
                impacted_warehouses.add(facility_id)
            elif kind == "store":
                impacted_stores.add(facility_id)
        issues.append(
            PrioritizedIssue(
                id=f"issue-{route.id}",
                severity=route.flood_exposure,
                subject=f"Risk on {route.origin_facility_id} to {route.destination_facility_id}",
                description="The baseline route crosses a road segment with high estimated flood exposure risk.",
            )
        )
    affected_products = {
        product_id
        for material in scenario.materials
        if material.supplier_id in impacted_suppliers
        for product_id in material.product_ids
    }
    impacted_orders = {
        order.id
        for order in scenario.orders
        if order.product_id in affected_products
        or order.preferred_warehouse_id in impacted_warehouses
        or order.store_id in impacted_stores
    }
    prices = {product.id: product.unit_price for product in scenario.products}
    exposure = sum(
        order.quantity * prices[order.product_id] for order in scenario.orders if order.id in impacted_orders
    )
    return OperationalImpact(
        impacted_supplier_ids=sorted(impacted_suppliers),
        impacted_warehouse_ids=sorted(impacted_warehouses),
        impacted_order_ids=sorted(impacted_orders),
        road_segments_at_risk=len(risky_segments),
        sales_exposure=Money(amount=exposure, currency="IDR"),
        issues=issues,
    )
