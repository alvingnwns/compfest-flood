from __future__ import annotations

from app.schemas.common import Money
from app.schemas.disruption import OperationalImpact, PrioritizedIssue, RoadRisk, Route
from app.schemas.scenario import Scenario


def calculate_impact(scenario: Scenario, road_risks: list[RoadRisk], routes: list[Route]) -> OperationalImpact:
    risky_segments = {road.segment_id for road in road_risks if road.risk_level in {"high", "critical"}}
    impacted_suppliers: set[str] = set()
    impacted_warehouses: set[str] = set()
    issues: list[PrioritizedIssue] = []
    facility_kind = {facility.id: facility.kind for facility in scenario.facilities}
    facility_name = {facility.id: facility.name for facility in scenario.facilities}
    baseline_routes: dict[tuple[str, str], Route] = {}
    for route in routes:
        if route.type != "baseline":
            continue
        baseline_routes[(route.origin_facility_id, route.destination_facility_id)] = route
        if not risky_segments.intersection(route.affected_road_segment_ids):
            continue
        for facility_id in (route.origin_facility_id, route.destination_facility_id):
            kind = facility_kind.get(facility_id)
            if kind == "supplier":
                impacted_suppliers.add(facility_id)
            elif kind == "warehouse":
                impacted_warehouses.add(facility_id)
        origin_name = facility_name.get(route.origin_facility_id, route.origin_facility_id)
        dest_name = facility_name.get(route.destination_facility_id, route.destination_facility_id)
        issues.append(
            PrioritizedIssue(
                id=f"issue-{route.id}",
                severity=route.flood_exposure,
                subject=f"Risiko pada rute {origin_name} \u2192 {dest_name}",
                description="Rute awal melewati segmen jalan dengan estimasi paparan banjir tinggi.",
            )
        )
    supplier_by_material = {material.id: material.supplier_id for material in scenario.materials}
    affected_products = {
        product.id
        for product in scenario.products
        if any(supplier_by_material.get(item.material_id) in impacted_suppliers for item in product.bom)
    }
    impacted_orders = {
        order.id
        for order in scenario.orders
        if order.product_id in affected_products
        or (
            (baseline_route := baseline_routes.get((order.preferred_warehouse_id, order.store_id))) is not None
            and bool(risky_segments.intersection(baseline_route.affected_road_segment_ids))
        )
    }
    prices = {product.id: product.unit_price for product in scenario.products}
    exposure = sum(
        order.quantity * prices[order.product_id] for order in scenario.orders if order.id in impacted_orders
    )
    severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return OperationalImpact(
        impacted_supplier_ids=sorted(impacted_suppliers),
        impacted_warehouse_ids=sorted(impacted_warehouses),
        impacted_order_ids=sorted(impacted_orders),
        road_segments_at_risk=len(risky_segments),
        sales_exposure=Money(amount=exposure, currency="IDR"),
        issues=sorted(issues, key=lambda issue: severity_rank[issue.severity], reverse=True),
    )
