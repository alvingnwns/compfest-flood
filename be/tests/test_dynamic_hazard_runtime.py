from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from app.errors import ApiError
from app.repositories.simulation_repository import simulation_repository
from app.schemas.simulation import RunSimulationRequest
from app.services.rainfall_scenario_service import get_rainfall_scenario, list_rainfall_scenarios
from app.services.relative_hazard_service import relative_hazard_index
from app.services.road_risk_fusion_service import dynamic_road_risk_score
from app.services.simulation_service import create_simulation
from app.services.temporal_hazard_service import MODEL_PATH, predict_temporal_hazard, temporal_model_provenance

BE_DIR = Path(__file__).resolve().parents[1]
RESEARCH_ANALYSIS = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase3b" / "fusion_analysis.json"
EXPECTED_MODEL_SHA256 = "043d9f9dd324166ec4dd403b713f5e8420ab606025dbadaac634e36498899d56"
EXPECTED_INDICES = {
    "Q1": 0.15223880597014924,
    "Q2": 0.4626865671641791,
    "Q3": 0.6462686567164179,
    "Q4": 0.7313432835820896,
}
EXPECTED_MEDIANS = {"Q1": 0.1103, "Q2": 0.1649, "Q3": 0.2064, "Q4": 0.2281}
EXPECTED_CATEGORIES = {
    "Q1": {"low": 1306, "medium": 83, "high": 24, "critical": 0},
    "Q2": {"low": 1144, "medium": 225, "high": 42, "critical": 2},
    "Q3": {"low": 923, "medium": 425, "high": 58, "critical": 7},
    "Q4": {"low": 817, "medium": 519, "high": 66, "critical": 11},
}


def _request(mode: str = "historical-replay", rainfall: str | None = None) -> RunSimulationRequest:
    return RunSimulationRequest(
        scenario_id="scenario-jakarta-20250304",
        analysis_mode=mode,
        region="jakarta",
        rainfall_scenario=rainfall,
    )


def _selected_paths(disruption) -> dict[tuple[str, str], tuple[str, ...]]:
    selected = {}
    for route in disruption.routes:
        selected[(route.origin_facility_id, route.destination_facility_id)] = tuple(route.affected_road_segment_ids)
    return selected


def test_frozen_scenarios_are_complete_immutable_and_provenanced() -> None:
    scenarios = list_rainfall_scenarios()
    assert [scenario.id for scenario in scenarios] == ["Q1", "Q2", "Q3", "Q4"]
    for scenario in scenarios:
        assert scenario.representative_sequence.shape == (30, 4)
        assert np.isfinite(scenario.representative_sequence).all()
        assert scenario.representative_sequence.flags.writeable is False
        assert scenario.provenance["sourceSplit"] == "train-2014-2018"
        assert scenario.provenance["probabilityCalibrated"] is False
        assert scenario.relative_hazard_index == EXPECTED_INDICES[scenario.id]
    with pytest.raises(ApiError, match="Skenario hujan tidak dikenal") as error:
        get_rainfall_scenario("Q5")
    assert error.value.code == "UNKNOWN_RAINFALL_SCENARIO"


def test_temporal_runtime_is_frozen_deterministic_and_uncalibrated() -> None:
    assert hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest() == EXPECTED_MODEL_SHA256
    provenance = temporal_model_provenance()
    assert provenance["modelSha256"] == EXPECTED_MODEL_SHA256
    assert provenance["modelType"] == "RandomForestClassifier"
    assert provenance["probabilityCalibrated"] is False
    for scenario in list_rainfall_scenarios():
        first = predict_temporal_hazard(scenario.representative_sequence)
        second = predict_temporal_hazard(scenario.representative_sequence.copy())
        assert first == second
        assert first.temporal_hazard_score == pytest.approx(scenario.temporal_hazard_score_research, abs=1e-15)
        assert 0 <= first.temporal_hazard_score <= 1
        assert first.probability_calibrated is False
        assert relative_hazard_index(scenario, first.temporal_hazard_score) == EXPECTED_INDICES[scenario.id]
    with pytest.raises(ApiError) as error:
        predict_temporal_hazard(np.zeros((29, 4)))
    assert error.value.code == "TEMPORAL_MODEL_INPUT_INVALID"


def test_fusion_matches_exact_phase3b_formula_and_invariants() -> None:
    static = [0.01, 0.2, 0.5, 0.8]
    dynamic_by_scenario = []
    for hazard_index in EXPECTED_INDICES.values():
        values = [dynamic_road_risk_score(value, hazard_index) for value in static]
        expected = [1 / (1 + math.exp(-(math.log(value / (1 - value)) + 1.5 * hazard_index))) for value in static]
        assert values == pytest.approx(expected, abs=1e-15)
        assert all(0 <= value <= 1 and math.isfinite(value) for value in values)
        assert values == sorted(values)
        dynamic_by_scenario.append(values)
    assert np.all(np.diff(np.asarray(dynamic_by_scenario), axis=0) > 0)


def test_historical_replay_golden_and_missing_mode_are_backward_compatible() -> None:
    simulation_repository.clear()
    missing_mode = create_simulation(RunSimulationRequest(scenario_id="scenario-jakarta-20250304"))
    explicit_mode = create_simulation(_request())
    assert missing_mode.id == explicit_mode.id
    assert missing_mode.analysis_mode == "historical-replay"
    assert missing_mode.hazard is None
    disruption = simulation_repository.get_disruption(missing_mode.id)
    assert disruption is not None
    roads = [
        (road.segment_id, road.risk_probability, road.risk_level, road.estimated_delay_minutes)
        for road in disruption.roads
    ]
    routes = [
        (
            route.type,
            route.origin_facility_id,
            route.destination_facility_id,
            route.affected_road_segment_ids,
            route.eta_minutes,
            route.flood_exposure,
            route.flood_exposure_probability,
        )
        for route in disruption.routes
    ]
    road_hash = hashlib.sha256(json.dumps(roads, separators=(",", ":")).encode()).hexdigest()
    route_hash = hashlib.sha256(json.dumps(routes, separators=(",", ":")).encode()).hexdigest()
    assert road_hash == "08c150334871a0c3a2fb7a227516a3a533c03f00c813c38bcf4be9f1aa8c3afc"
    assert route_hash == "51039933930c8ce5536b937cb668ecb8367f088784284b91d93d08ea09de7740"
    provenance_hash = hashlib.sha256(
        json.dumps(
            missing_mode.model_provenance.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    assert provenance_hash == "81b8d80227c4c048fbf657c827e096bf9938752867a18c66e7c8edf82464bf94"
    assert all(road.dynamic_road_risk_score is None for road in disruption.roads)


def test_dynamic_simulation_reproduces_phase3b_and_changes_networkx_paths() -> None:
    simulation_repository.clear()
    road_scores: dict[str, np.ndarray] = {}
    selected_paths = {}
    research = json.loads(RESEARCH_ANALYSIS.read_text(encoding="utf-8"))
    for scenario_id in EXPECTED_INDICES:
        simulation = create_simulation(_request("scenario-simulation", scenario_id))
        disruption = simulation_repository.get_disruption(simulation.id)
        assert disruption is not None
        assert simulation.hazard is not None
        assert simulation.hazard.rainfall_scenario == scenario_id
        assert simulation.hazard.relative_hazard_index == EXPECTED_INDICES[scenario_id]
        assert simulation.hazard.probability_calibrated is False
        assert len(disruption.roads) == 1413
        values = np.asarray([road.dynamic_road_risk_score for road in disruption.roads], dtype=np.float64)
        assert np.isfinite(values).all()
        assert np.all((values >= 0) & (values <= 1))
        assert np.median(values) == pytest.approx(EXPECTED_MEDIANS[scenario_id], abs=5e-5)
        counts = Counter(road.risk_level for road in disruption.roads)
        assert {level: counts.get(level, 0) for level in EXPECTED_CATEGORIES[scenario_id]} == EXPECTED_CATEGORIES[
            scenario_id
        ]
        assert all(road.dynamic_risk_score_semantics for road in disruption.roads)
        road_scores[scenario_id] = values
        selected_paths[scenario_id] = _selected_paths(disruption)

    matrix = np.vstack([road_scores[scenario] for scenario in EXPECTED_INDICES])
    assert np.all(np.diff(matrix, axis=0) > 0)
    assert np.count_nonzero((matrix[-1] - matrix[0]) >= 0.05) == 1262
    changed = sum(selected_paths["Q1"][pair] != selected_paths["Q4"][pair] for pair in selected_paths["Q1"])
    assert changed == 9
    assert research["selectedCandidate"] == {"method": "logit_shift", "parameter": 1.5}


def test_analysis_mode_region_and_scenario_errors_use_api_conventions() -> None:
    with pytest.raises(ApiError) as error:
        create_simulation(_request("unknown"))
    assert error.value.code == "UNKNOWN_ANALYSIS_MODE"
    with pytest.raises(ApiError) as error:
        create_simulation(
            RunSimulationRequest(
                scenario_id="scenario-jakarta-20250304",
                analysis_mode="scenario-simulation",
                region="bandung",
                rainfall_scenario="Q1",
            )
        )
    assert error.value.code == "UNSUPPORTED_REGION"
    with pytest.raises(ApiError) as error:
        create_simulation(_request("scenario-simulation"))
    assert error.value.code == "UNKNOWN_RAINFALL_SCENARIO"

    simulation_repository.clear()
    for _ in range(2):
        with pytest.raises(ApiError) as error:
            create_simulation(_request("scenario-simulation", "Q5"))
        assert error.value.code == "UNKNOWN_RAINFALL_SCENARIO"
    valid = create_simulation(_request())
    assert valid.id.endswith("-001")
