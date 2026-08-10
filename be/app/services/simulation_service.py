from __future__ import annotations

from datetime import datetime, timezone

from app.errors import ApiError

from app.repositories.geospatial_repository import get_road_features, get_historical_flood_extent
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.simulation import Simulation
from app.schemas.disruption import DisruptionAnalysis, RoadSegmentRisk
from app.services.flood_risk_service import predict_risk
from app.services.routing_service import calculate_routes
from app.services.impact_service import calculate_impact


def create_simulation(scenario_id: str) -> Simulation:
    scenario = get_historical_jakarta()
    if scenario_id != scenario.id:
        raise ApiError(404, "scenario_not_found", "Scenario not found.", details={"scenarioId": scenario_id})

    created_at = datetime.now(timezone.utc)
    simulation = Simulation(
        id=simulation_repository.next_id(scenario_id),
        scenario_id=scenario_id,
        status="queued",
        created_at=created_at,
        data_mode=scenario.data_sources.mode,
        historical_data_status=scenario.data_sources.historical_status,
    )
    simulation_repository.save(simulation)

    # Phase 3 & 4: Run flood risk inference and build disruption analysis
    road_features = get_road_features()
    road_risks_map = {}
    
    for feature in road_features.get("features", []):
        props = feature.get("properties", {})
        risk = predict_risk(props)
        road_risks_map[props.get("segmentId")] = risk.model_dump()

    routes = []
    pairs = [
        ("sup-a", "fac-1"),
        ("sup-b", "fac-1"),
        ("fac-1", "wh-east"),
        ("fac-1", "wh-west")
    ]
    for orig, dest in pairs:
        routes.extend(calculate_routes(orig, dest, road_risks_map))
        
    road_risks = []
    for feature in road_features.get("features", []):
        props = feature.get("properties", {})
        seg_id = props.get("segmentId")
        risk = road_risks_map.get(seg_id, {})
        
        aff_sups = set()
        aff_whs = set()
        for r in routes:
            if r.type == "baseline" and seg_id in r.affected_road_segment_ids:
                if r.origin_facility_id.startswith("sup"):
                    aff_sups.add(r.origin_facility_id)
                if r.destination_facility_id.startswith("wh"):
                    aff_whs.add(r.destination_facility_id)
                    
        road_risks.append(RoadSegmentRisk(
            segment_id=seg_id,
            road_name=props.get("roadName", "Unknown"),
            geometry=feature.get("geometry"),
            risk_probability=risk.get("riskProbability", 0.0),
            risk_level=risk.get("riskLevel", "low"),
            estimated_delay_minutes=risk.get("estimatedDelayMinutes"),
            risk_factors=risk.get("riskFactors", []),
            affected_supplier_ids=list(aff_sups),
            affected_warehouse_ids=list(aff_whs),
            affected_order_ids=[]
        ))
        
    impact = calculate_impact(road_risks, routes)
    
    disruption = DisruptionAnalysis(
        simulation_id=simulation.id,
        facilities=scenario.facilities,
        historical_flood_geometry=get_historical_flood_extent(),
        roads=road_risks,
        routes=routes,
        impact=impact
    )
    
    simulation_repository.save_disruption(simulation.id, disruption)

    completed = simulation.model_copy(
        update={
            "status": "completed",
            "completed_at": datetime.now(timezone.utc),
            "model_version": "flood-risk-1.0.0",
        }
    )
    return simulation_repository.save(completed)


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
