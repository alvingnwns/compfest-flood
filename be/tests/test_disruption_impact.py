from app.repositories.scenario_repository import get_historical_jakarta
from app.schemas.disruption import RoadRisk, Route
from app.services.impact_service import calculate_impact


def _road(segment_id: str, risk_level: str) -> RoadRisk:
    probability = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 0.8}[risk_level]
    return RoadRisk(
        segment_id=segment_id,
        road_name=segment_id,
        geometry={"type": "LineString", "coordinates": [[106.8, -6.2], [106.81, -6.21]]},
        risk_probability=probability,
        risk_level=risk_level,
        estimated_delay_minutes=1,
        risk_factors=[],
        affected_supplier_ids=[],
        affected_warehouse_ids=[],
        affected_order_ids=[],
    )


def _route(origin: str, destination: str, segment_id: str, risk_level: str) -> Route:
    probability = {"low": 0.1, "medium": 0.3, "high": 0.6, "critical": 0.8}[risk_level]
    return Route(
        id=f"route-baseline-{origin}-{destination}",
        type="baseline",
        origin_facility_id=origin,
        destination_facility_id=destination,
        geometry={"type": "LineString", "coordinates": [[106.8, -6.2], [106.81, -6.21]]},
        distance_km=1,
        eta_minutes=5,
        flood_exposure=risk_level,
        flood_exposure_probability=probability,
        affected_road_segment_ids=[segment_id],
    )


def test_high_and_critical_segments_are_the_only_segments_counted_as_risky() -> None:
    scenario = get_historical_jakarta()
    roads = [_road("low", "low"), _road("medium", "medium"), _road("high", "high"), _road("critical", "critical")]

    impact = calculate_impact(scenario, roads, [])

    assert impact.road_segments_at_risk == 2


def test_orders_use_their_own_preferred_baseline_route_not_unrelated_facility_routes() -> None:
    scenario = get_historical_jakarta()
    roads = [_road("medium", "medium"), _road("high", "high")]
    routes = [
        _route("wh-east", "store-c", "high", "high"),
        _route("wh-east", "store-d", "medium", "medium"),
        _route("wh-west", "store-d", "high", "high"),
    ]

    impact = calculate_impact(scenario, roads, routes)

    assert impact.impacted_supplier_ids == []
    assert impact.impacted_order_ids == ["ORD-003", "ORD-008", "ORD-013", "ORD-018"]
    assert impact.sales_exposure.amount == 30_400_000
    assert "ORD-004" not in impact.impacted_order_ids


def test_supplier_risk_propagates_only_to_products_linked_to_that_supplier() -> None:
    demo = get_historical_jakarta()
    selected = [order for order in demo.orders if order.id in {"ORD-001", "ORD-002"}]
    scenario = demo.model_copy(deep=True, update={"orders": selected})
    roads = [_road("medium", "medium"), _road("high", "high")]
    routes = [
        _route("sup-a", "fac-1", "high", "high"),
        _route("wh-west", "store-a", "medium", "medium"),
        _route("wh-west", "store-b", "medium", "medium"),
    ]

    impact = calculate_impact(scenario, roads, routes)

    assert impact.impacted_supplier_ids == ["sup-a"]
    assert impact.impacted_order_ids == ["ORD-002"]


def test_custom_two_order_exposure_and_price_doubling_are_direct_and_linear() -> None:
    demo = get_historical_jakarta()
    orders = [order for order in demo.orders if order.id in {"ORD-001", "ORD-002"}]
    scenario = demo.model_copy(deep=True, update={"orders": orders})
    roads = [_road("medium", "medium"), _road("high", "high")]
    routes = [
        _route("wh-west", "store-a", "high", "high"),
        _route("wh-west", "store-b", "medium", "medium"),
    ]

    baseline = calculate_impact(scenario, roads, routes)
    doubled = scenario.model_copy(
        deep=True,
        update={
            "products": [
                product.model_copy(update={"unit_price": product.unit_price * 2}) for product in scenario.products
            ]
        },
    )
    doubled_impact = calculate_impact(doubled, roads, routes)

    assert baseline.impacted_order_ids == ["ORD-001"]
    assert baseline.sales_exposure.amount == 4_800_000
    assert doubled_impact.impacted_order_ids == baseline.impacted_order_ids
    assert doubled_impact.sales_exposure.amount == 9_600_000


def test_priority_issues_are_stably_sorted_critical_before_high() -> None:
    scenario = get_historical_jakarta()
    roads = [_road("high-1", "high"), _road("critical", "critical"), _road("high-2", "high")]
    routes = [
        _route("wh-east", "store-a", "high-1", "high"),
        _route("wh-east", "store-b", "critical", "critical"),
        _route("wh-east", "store-c", "high-2", "high"),
    ]

    impact = calculate_impact(scenario, roads, routes)

    assert [issue.severity for issue in impact.issues] == ["critical", "high", "high"]
    assert [issue.id for issue in impact.issues[1:]] == [
        "issue-route-baseline-wh-east-store-a",
        "issue-route-baseline-wh-east-store-c",
    ]
