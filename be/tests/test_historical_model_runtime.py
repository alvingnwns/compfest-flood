from __future__ import annotations

import pytest

from app.errors import ApiError
from app.repositories.geospatial_repository import get_road_features
from app.repositories.scenario_repository import get_historical_jakarta
from app.repositories.simulation_repository import simulation_repository
from app.schemas.recovery import RecoveryConstraints
from app.services.flood_risk_service import (
    HISTORICAL_MODEL_SHA256,
    model_version,
    predict_risk,
    verify_historical_model_artifact,
)
from app.services.recovery_service import generate_recovery_plan
from app.services.routing_service import calculate_routes


def test_historical_model_probabilities_change_real_osm_route() -> None:
    roads = get_road_features()["features"]
    risks = {feature["properties"]["segmentId"]: predict_risk(feature["properties"]).model_dump() for feature in roads}
    routes = calculate_routes("wh-west", "store-a", risks)
    assert model_version() == "indonesia-road-corridor-flood-exposure-v1"
    assert [route.type for route in routes] == ["baseline", "recovery"]
    assert len(routes[0].affected_road_segment_ids) == 33
    assert len(routes[1].affected_road_segment_ids) == 31
    assert routes[0].affected_road_segment_ids != routes[1].affected_road_segment_ids


def test_historical_model_artifact_hash_is_verified() -> None:
    assert verify_historical_model_artifact() == HISTORICAL_MODEL_SHA256
    with pytest.raises(ApiError) as raised:
        verify_historical_model_artifact(expected_sha256="0" * 64)
    assert raised.value.code == "model_integrity_invalid"


def test_historical_model_route_reaches_recovery_and_business_outputs(simulation_id: str) -> None:
    simulation = simulation_repository.get(simulation_id)
    disruption = simulation_repository.get_disruption(simulation_id)
    assert simulation.model_version == "indonesia-road-corridor-flood-exposure-v1"
    assert any(route.type == "recovery" for route in disruption.routes)
    scenario = get_historical_jakarta()
    plan = generate_recovery_plan(
        simulation_id,
        scenario,
        disruption,
        RecoveryConstraints(allow_substitution=True, max_additional_delay_minutes=30),
    )
    assert plan.manufacturing_actions
    assert plan.logistics_actions
    assert plan.commerce_actions
    assert plan.recovery_order_outcomes
    assert any(action.recovery_route_id for action in plan.logistics_actions)
