from app.repositories.scenario_repository import get_historical_jakarta
from app.schemas.disruption import OperationalImpact, PrioritizedIssue, RoadRisk, Route
from app.schemas.common import Money

def calculate_impact(road_risks: list[RoadRisk], routes: list[Route]) -> OperationalImpact:
    scenario = get_historical_jakarta()

    impacted_suppliers = set()
    impacted_warehouses = set()
    impacted_orders = set()
    segments_at_risk = 0
    sales_exposure = 0.0
    issues = []

    # 1. Find segments at risk
    at_risk_segment_ids = set()
    for road in road_risks:
        if road.risk_level in ["high", "critical"]:
            segments_at_risk += 1
            at_risk_segment_ids.add(road.segment_id)

    # 2. Check which routes use these segments
    for route in routes:
        if route.type == "baseline":
            overlap = set(route.affected_road_segment_ids).intersection(at_risk_segment_ids)
            if overlap:
                orig = route.origin_facility_id
                dest = route.destination_facility_id

                for fac in scenario.facilities:
                    if fac.id == orig and fac.kind == "supplier":
                        impacted_suppliers.add(orig)
                        issues.append(
                            PrioritizedIssue(
                                id=f"issue-sup-{orig}",
                                severity="high",
                                subject=f"Supplier {fac.name} inbound route",
                                description="High estimated disruption risk on baseline route.",
                            )
                        )
                    if fac.id == dest and fac.kind == "warehouse":
                        impacted_warehouses.add(dest)
                        issues.append(
                            PrioritizedIssue(
                                id=f"issue-wh-{dest}",
                                severity="high",
                                subject=f"Warehouse {fac.name} inbound route",
                                description="High estimated disruption risk from factory to warehouse.",
                            )
                        )

    # 3. Determine impacted orders (Simple heuristic for MVP)
    for order in scenario.orders:
        order_impacted = False

        if "sup-a" in impacted_suppliers and order.product_id == "prod-a":
            order_impacted = True
        if "sup-b" in impacted_suppliers and order.product_id == "prod-b":
            order_impacted = True

        if "wh-east" in impacted_warehouses and order.store_id in ["store-c", "store-d"]:
            order_impacted = True
        if "wh-west" in impacted_warehouses and order.store_id in ["store-a", "store-b", "store-e"]:
            order_impacted = True

        if order_impacted:
            impacted_orders.add(order.id)
            # 100,000 IDR per unit
            sales_exposure += order.quantity * 100000.0

    unique_issues = []
    seen = set()
    for issue in issues:
        if issue.id not in seen:
            seen.add(issue.id)
            unique_issues.append(issue)

    # If no issues but there are segments at risk, add a generic issue
    if not unique_issues and segments_at_risk > 0:
        unique_issues.append(
            PrioritizedIssue(
                id="issue-generic-risk",
                severity="medium",
                subject="General Road Risk",
                description=f"{segments_at_risk} road segments have high disruption risk.",
            )
        )

    return OperationalImpact(
        impacted_supplier_ids=list(impacted_suppliers),
        impacted_warehouse_ids=list(impacted_warehouses),
        impacted_order_ids=list(impacted_orders),
        road_segments_at_risk=segments_at_risk,
        sales_exposure=Money(amount=sales_exposure, currency="IDR"),
        issues=unique_issues,
    )
