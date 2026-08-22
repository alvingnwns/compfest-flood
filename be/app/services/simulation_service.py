from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from app.business_import.mapper import apply_snapshot_to_scenario
from app.business_import.service import get_business_snapshot
from app.errors import ApiError
from app.repositories.geospatial_repository import get_historical_flood_extent, get_road_features
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.disruption import DisruptionAnalysis, RoadRisk
from app.schemas.scenario import Inventory, Scenario, Vehicle
from app.schemas.simulation import DynamicHazardMetadata, ModelProvenance, RunSimulationRequest, Simulation
from app.services.flood_risk_service import model_provenance, model_version, predict_risk
from app.services.impact_service import calculate_impact
from app.services.rainfall_scenario_service import get_rainfall_scenario
from app.services.relative_hazard_service import relative_hazard_index
from app.services.road_risk_fusion_service import (
    FUSION_BETA,
    FUSION_METHOD,
    dynamic_road_risk_score,
    routing_band,
)
from app.services.routing_service import calculate_routes
from app.services.temporal_hazard_service import predict_temporal_hazard

HISTORICAL_REPLAY = "historical-replay"
SCENARIO_SIMULATION = "scenario-simulation"


def _apply_overrides(scenario: Scenario, request: RunSimulationRequest) -> Scenario:
    """Return a deep copy of scenario with operational overrides applied."""
    if not request.vehicle_overrides and not request.custom_vehicles and not request.inventory_overrides:
        return scenario

    base_vehicle_ids = {vehicle.id for vehicle in scenario.vehicles}
    custom_vehicle_ids: set[str] = set()
    for custom in request.custom_vehicles:
        if custom.id in base_vehicle_ids or custom.id in custom_vehicle_ids:
            raise ApiError(
                422,
                "DUPLICATE_VEHICLE_ID",
                "ID kendaraan harus unik.",
                details={"vehicleId": custom.id},
            )
        custom_vehicle_ids.add(custom.id)

    unknown_override_ids = sorted({ov.id for ov in request.vehicle_overrides} - base_vehicle_ids)
    if unknown_override_ids:
        raise ApiError(
            422,
            "UNKNOWN_VEHICLE_OVERRIDE",
            "Override hanya dapat diterapkan pada kendaraan utama.",
            details={"vehicleIds": unknown_override_ids},
        )

    vehicle_map = {ov.id: ov for ov in request.vehicle_overrides}
    new_vehicles: list[Vehicle] = []
    for vehicle in scenario.vehicles:
        ov = vehicle_map.get(vehicle.id)
        if ov is None:
            new_vehicles.append(vehicle)
        else:
            new_vehicles.append(
                vehicle.model_copy(
                    update={
                        k: v
                        for k, v in {
                            "available": ov.available,
                            "capacity_units": ov.capacity_units,
                        }.items()
                        if v is not None
                    }
                )
            )

    new_vehicles.extend(
        Vehicle(
            id=custom.id,
            label=custom.label,
            capacity_units=custom.capacity_units,
            available=custom.available,
        )
        for custom in request.custom_vehicles
    )

    inventory_index = {(ov.facility_id, ov.product_id): ov.quantity for ov in request.inventory_overrides}
    new_inventory: list[Inventory] = []
    for item in scenario.inventory:
        key = (item.facility_id, item.product_id)
        if key in inventory_index:
            new_inventory.append(item.model_copy(update={"quantity": inventory_index[key]}))
        else:
            new_inventory.append(item)

    return scenario.model_copy(update={"vehicles": new_vehicles, "inventory": new_inventory})


def _override_fingerprint(request: RunSimulationRequest) -> str:
    """Stable hash of operational overrides so different configs create distinct simulations."""
    payload = json.dumps(
        {
            "analysisMode": request.analysis_mode,
            "region": request.region,
            "rainfallScenario": request.rainfall_scenario,
            "businessSnapshotId": request.business_snapshot_id,
            "vehicleOverrides": [ov.model_dump(mode="json") for ov in request.vehicle_overrides],
            "customVehicles": [
                vehicle.model_dump(mode="json") for vehicle in sorted(request.custom_vehicles, key=lambda item: item.id)
            ],
            "inventoryOverrides": [ov.model_dump(mode="json") for ov in request.inventory_overrides],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def create_simulation(request: RunSimulationRequest) -> Simulation:
    if request.analysis_mode not in {HISTORICAL_REPLAY, SCENARIO_SIMULATION}:
        raise ApiError(
            422,
            "UNKNOWN_ANALYSIS_MODE",
            "Mode analisis tidak dikenal.",
            details={"analysisMode": request.analysis_mode},
        )
    if request.region != "jakarta":
        raise ApiError(
            422,
            "UNSUPPORTED_REGION",
            "Region belum didukung untuk simulasi dynamic hazard.",
            details={"region": request.region, "supported": ["jakarta"]},
        )
    if request.analysis_mode == SCENARIO_SIMULATION and request.rainfall_scenario is None:
        raise ApiError(
            422,
            "UNKNOWN_RAINFALL_SCENARIO",
            "rainfallScenario wajib untuk scenario-simulation.",
            details={"supported": ["Q1", "Q2", "Q3", "Q4"]},
        )

    demo_scenario = get_historical_jakarta()
    if request.scenario_id != demo_scenario.id:
        raise ApiError(
            404, "scenario_not_found", "Skenario tidak ditemukan.", details={"scenarioId": request.scenario_id}
        )

    rainfall = None
    temporal = None
    hazard_index = None
    if request.analysis_mode == SCENARIO_SIMULATION:
        rainfall = get_rainfall_scenario(request.rainfall_scenario or "")
        temporal = predict_temporal_hazard(rainfall.representative_sequence)
        hazard_index = relative_hazard_index(rainfall, temporal.temporal_hazard_score)

    scenario = demo_scenario
    business_source = "demo"
    if request.business_snapshot_id:
        snapshot = get_business_snapshot(request.business_snapshot_id)
        scenario = apply_snapshot_to_scenario(
            demo_scenario,
            products=snapshot.products,
            orders=snapshot.orders,
            inventory=snapshot.inventory,
            materials=snapshot.materials,
        )
        business_source = "custom"
    effective_scenario = _apply_overrides(scenario, request)

    override_key = _override_fingerprint(request)
    existing = simulation_repository.get_for_scenario(request.scenario_id, override_key)
    if existing is not None:
        return existing

    simulation = Simulation(
        id=simulation_repository.next_id(request.scenario_id),
        scenario_id=request.scenario_id,
        status="queued",
        created_at=datetime.now(UTC),
        data_mode=scenario.data_sources.mode,
        historical_data_status=scenario.data_sources.historical_status,
        business_data_source=business_source,
        business_snapshot_id=request.business_snapshot_id,
        analysis_mode=request.analysis_mode,
        region="jakarta",
    )
    simulation_repository.save(simulation, override_key)
    simulation_repository.save_effective_scenario(simulation.id, effective_scenario)
    road_features = get_road_features().get("features", [])
    static_risk_results = {
        feature["properties"]["segmentId"]: predict_risk(feature["properties"]).model_dump()
        for feature in road_features
    }
    hazard_metadata = None
    if request.analysis_mode == HISTORICAL_REPLAY:
        risk_results = static_risk_results
    else:
        if rainfall is None or temporal is None or hazard_index is None:
            raise ApiError(500, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Dynamic hazard context tidak tersedia.")
        risk_results = {}
        for segment_id, static in static_risk_results.items():
            dynamic_score = dynamic_road_risk_score(static["riskProbability"], hazard_index)
            risk_results[segment_id] = {
                **static,
                "staticRoadSusceptibility": static["riskProbability"],
                "riskProbability": dynamic_score,
                "riskLevel": routing_band(dynamic_score),
                "dynamicRoadRiskScore": dynamic_score,
            }
        hazard_metadata = DynamicHazardMetadata(
            rainfall_scenario=rainfall.id,
            temporal_hazard_score=temporal.temporal_hazard_score,
            relative_hazard_index=hazard_index,
            probability_calibrated=False,
            model_version=temporal.model_version,
            model_type=temporal.model_type,
            fusion_method=FUSION_METHOD,
            fusion_beta=FUSION_BETA,
            risk_level_semantics="routing compatibility band from unchanged static-model thresholds",
        )
    suppliers = [facility for facility in effective_scenario.facilities if facility.kind == "supplier"]
    factories = [facility for facility in effective_scenario.facilities if facility.kind == "factory"]
    warehouses = [facility for facility in effective_scenario.facilities if facility.kind == "warehouse"]
    stores = [facility for facility in effective_scenario.facilities if facility.kind == "store"]
    pairs = {(supplier.id, factory.id) for supplier in suppliers for factory in factories}
    pairs.update((warehouse.id, store.id) for warehouse in warehouses for store in stores)
    routes = [
        route for origin, destination in sorted(pairs) for route in calculate_routes(origin, destination, risk_results)
    ]

    material_products = {material.supplier_id: set(material.product_ids) for material in effective_scenario.materials}
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
            for order in effective_scenario.orders
            if order.product_id in affected_products
            or order.preferred_warehouse_id in affected_warehouses
            or order.store_id in affected_stores
        }
        osm_way_ids = properties.get("osmWayIds") or []
        if not isinstance(osm_way_ids, list):
            osm_way_ids = [osm_way_ids]
        roads.append(
            RoadRisk(
                segment_id=segment_id,
                road_name=properties.get("roadName", "Jalan tanpa nama"),
                highway_class=properties.get("highway"),
                osm_way_ids=[str(w) for w in osm_way_ids if w is not None],
                geometry=feature["geometry"],
                risk_probability=static_risk_results[segment_id]["riskProbability"],
                dynamic_road_risk_score=risk.get("dynamicRoadRiskScore"),
                dynamic_risk_score_semantics=(
                    "scenario-conditioned relative road-risk score; not a calibrated probability"
                    if request.analysis_mode == SCENARIO_SIMULATION
                    else None
                ),
                routing_band_basis=(
                    "unchanged static-model thresholds used only for routing compatibility"
                    if request.analysis_mode == SCENARIO_SIMULATION
                    else None
                ),
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
        facilities=effective_scenario.facilities,
        historical_flood_geometry=get_historical_flood_extent().get("features", [{}])[0].get("geometry"),
        roads=roads,
        routes=routes,
        impact=calculate_impact(effective_scenario, roads, routes),
    )
    simulation_repository.save_disruption(simulation.id, disruption)
    return simulation_repository.save(
        simulation.model_copy(
            update={
                "status": "completed",
                "completed_at": datetime.now(UTC),
                "model_version": model_version(),
                "model_provenance": ModelProvenance.model_validate(model_provenance()),
                "optimizer_version": "cp-sat-connected-v2",
                "hazard": hazard_metadata,
            }
        ),
        override_key,
    )


def get_simulation(simulation_id: str) -> Simulation:
    simulation = simulation_repository.get(simulation_id)
    if simulation is None:
        raise ApiError(
            404,
            "simulation_not_found",
            "Simulasi tidak ditemukan.",
            details={"simulationId": simulation_id},
        )
    return simulation
