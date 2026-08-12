from __future__ import annotations

from datetime import UTC, datetime

from app.errors import ApiError
from app.repositories.geospatial_repository import get_historical_flood_extent, get_road_features
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.disruption import DisruptionAnalysis, RoadRisk
from app.schemas.simulation import Simulation
from app.services.flood_risk_service import model_version, predict_risk
from app.services.impact_service import calculate_impact
from app.services.routing_service import calculate_routes


def create_simulation(scenario_id: str) -> Simulation:
    scenario = get_historical_jakarta()
    if scenario_id != scenario.id:
        raise ApiError(404, "scenario_not_found", "Scenario not found.", details={"scenarioId": scenario_id})
    existing = simulation_repository.get_for_scenario(scenario_id)
    if existing is not None:
        return existing
    simulation = Simulation(
        id=simulation_repository.next_id(scenario_id),
        scenario_id=scenario_id,
        status="queued",
        created_at=datetime.now(UTC),
        data_mode=scenario.data_sources.mode,
        historical_data_status=scenario.data_sources.historical_status,
    )
    simulation_repository.save(simulation)
    road_features = get_road_features().get("features", [])
    risk_results = {
        feature["properties"]["segmentId"]: predict_risk(feature["properties"]).model_dump()
        for feature in road_features
    }
    suppliers = [facility for facility in scenario.facilities if facility.kind == "supplier"]
    factories = [facility for facility in scenario.facilities if facility.kind == "factory"]
    warehouses = [facility for facility in scenario.facilities if facility.kind == "warehouse"]
    stores = [facility for facility in scenario.facilities if facility.kind == "store"]
    pairs = {(supplier.id, factory.id) for supplier in suppliers for factory in factories}
    pairs.update((warehouse.id, store.id) for warehouse in warehouses for store in stores)
    routes = [
        route for origin, destination in sorted(pairs) for route in calculate_routes(origin, destination, risk_results)
    ]

    material_products = {material.supplier_id: set(material.product_ids) for material in scenario.materials}
    roads = []
    for feature in road_features:
        properties = feature["properties"]
        segment_id = properties["segmentId"]
        risk = risk_results[segment_id]
        baseline_routes = [
            route for route in routes if route.type == "baseline" and segment_id in route.affected_road_segment_ids
        ]
        affected_suppliers = {
            route.origin_facility_id for route in baseline_routes if route.origin_facility_id in material_products
        }
        affected_warehouses = {
            facility_id
            for route in baseline_routes
            for facility_id in (route.origin_facility_id, route.destination_facility_id)
            if any(warehouse.id == facility_id for warehouse in warehouses)
        }
        affected_stores = {
            route.destination_facility_id
            for route in baseline_routes
            if route.destination_facility_id in {store.id for store in stores}
        }
        affected_products = {
            product_id for supplier_id in affected_suppliers for product_id in material_products[supplier_id]
        }
        affected_orders = {
            order.id
            for order in scenario.orders
            if order.product_id in affected_products
            or order.preferred_warehouse_id in affected_warehouses
            or order.store_id in affected_stores
        }
        roads.append(
            RoadRisk(
                segment_id=segment_id,
                road_name=properties.get("roadName", "Unknown"),
                geometry=feature["geometry"],
                risk_probability=risk["riskProbability"],
                risk_level=risk["riskLevel"],
                estimated_delay_minutes=risk["estimatedDelayMinutes"],
                risk_factors=risk["riskFactors"],
                affected_supplier_ids=sorted(affected_suppliers),
                affected_warehouse_ids=sorted(affected_warehouses),
                affected_order_ids=sorted(affected_orders),
            )
        )
    disruption = DisruptionAnalysis(
        simulation_id=simulation.id,
        facilities=scenario.facilities,
        historical_flood_geometry=get_historical_flood_extent().get("features", [{}])[0].get("geometry"),
        roads=roads,
        routes=routes,
        impact=calculate_impact(scenario, roads, routes),
    )
    simulation_repository.save_disruption(simulation.id, disruption)
    return simulation_repository.save(
        simulation.model_copy(
            update={
                "status": "completed",
                "completed_at": datetime.now(UTC),
                "model_version": model_version(),
                "optimizer_version": "cp-sat-connected-v2",
            }
        )
    )


def get_simulation(simulation_id: str) -> Simulation:
    simulation = simulation_repository.get(simulation_id)
    if simulation is None:
        raise ApiError(
            404,
            "simulation_not_found",
            "Simulation not found.",
            details={"simulationId": simulation_id},
        )
    return simulation
