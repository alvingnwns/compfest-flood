from __future__ import annotations

from datetime import datetime, timezone

from app.errors import ApiError
from app.repositories.geospatial_repository import get_road_features
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.simulation import Simulation
from app.services.flood_risk_service import predict_risk


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

    # The local MVP has no background worker yet. The synchronous orchestration
    # boundary preserves the contract lifecycle while keeping replay deterministic.
    
    # Phase 3: Run flood risk inference for all road segments
    road_features = get_road_features()
    for feature in road_features.get("features", []):
        props = feature.get("properties", {})
        risk = predict_risk(props)
        # For now, just prove the model works by evaluating it; 
        # Phase 4 will persist these to the disruption endpoint.
        pass

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
