from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.stats import spearmanr

from app.repositories.geospatial_repository import get_road_features, get_routing_graph
from app.services.flood_risk_service import predict_risk
from app.services.routing_service import calculate_routes
from dynamic_hazard.common import file_sha256, load_frozen_model, load_split, save_json

BE_DIR = Path(__file__).resolve().parents[2]
PHASE2_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase2"
PHASE3A_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase3a"
DEFAULT_OUTPUT_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase3b"
ROAD_MODEL_PATH = BE_DIR / "app" / "models" / "flood_risk_model.joblib"
ROAD_FEATURES_PATH = BE_DIR / "app" / "data" / "roads" / "jakarta-2025-03-04-road-features.geojson"
ROUTING_GRAPH_PATH = BE_DIR / "app" / "data" / "roads" / "jakarta-2025-03-04-routing-graph.json"
TEMPORAL_MODEL_PATH = PHASE2_DIR / "selected_model.joblib"
PHASE3A_ANALYSIS_PATH = PHASE3A_DIR / "scenario_analysis.json"
REPRESENTATIVES_PATH = PHASE3A_DIR / "representative_sequences.npz"

EXPECTED_ROAD_COUNT = 1_413
EXPECTED_TEMPORAL_MODEL_SHA256 = "49efd3931bc3b0030ffaa32beefac56375a19826901c4b3f2b487945c37f450c"
EXPECTED_ROAD_MODEL_SHA256 = "6a087f31a8a80d77bce64bedb74b04c88e0c8269b4cc767bb3cc3984e199a78d"
PARAMETERS = (0.25, 0.5, 0.75, 1.0, 1.5)
SCENARIO_IDS = ("Q1", "Q2", "Q3", "Q4")
PERCENTILES = (0, 0.25, 0.5, 0.75, 0.9, 0.95, 1)
RISK_LEVELS = ("low", "medium", "high", "critical")


def _sha256_text(values: list[str]) -> str:
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _finite_float(value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Research artifacts may not contain NaN or infinity.")
    return result


def _distribution(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("Distribution input must be a finite one-dimensional array.")
    quantiles = np.quantile(values, PERCENTILES)
    return {
        "minimum": _finite_float(quantiles[0]),
        "p25": _finite_float(quantiles[1]),
        "median": _finite_float(quantiles[2]),
        "mean": _finite_float(values.mean()),
        "p75": _finite_float(quantiles[3]),
        "p90": _finite_float(quantiles[4]),
        "p95": _finite_float(quantiles[5]),
        "maximum": _finite_float(quantiles[6]),
        "variance": _finite_float(values.var()),
    }


def _risk_level(values: np.ndarray, thresholds: dict[str, float]) -> np.ndarray:
    return np.select(
        [values < thresholds["low"], values < thresholds["medium"], values < thresholds["high"]],
        ["low", "medium", "high"],
        default="critical",
    )


def _category_counts(values: np.ndarray, thresholds: dict[str, float]) -> dict[str, int]:
    counts = Counter(_risk_level(values, thresholds))
    return {level: int(counts.get(level, 0)) for level in RISK_LEVELS}


def empirical_percentile_rank(train_scores: np.ndarray, value: float) -> float:
    """Mid-rank empirical CDF using train scores only."""
    train_scores = np.asarray(train_scores, dtype=np.float64)
    if train_scores.ndim != 1 or not len(train_scores) or not np.isfinite(train_scores).all():
        raise ValueError("Train scores must be a non-empty finite vector.")
    below = np.count_nonzero(train_scores < value)
    equal = np.count_nonzero(train_scores == value)
    return float(np.clip((below + 0.5 * equal) / len(train_scores), 0.0, 1.0))


def multiplicative_modulation(static: np.ndarray, hazard_index: float, parameter: float) -> np.ndarray:
    return np.clip(static * (1.0 + parameter * hazard_index), 0.0, 1.0)


def logit_shift(static: np.ndarray, hazard_index: float, parameter: float) -> np.ndarray:
    clipped = np.clip(static, 1e-9, 1.0 - 1e-9)
    logit = np.log(clipped / (1.0 - clipped))
    return 1.0 / (1.0 + np.exp(-(logit + parameter * hazard_index)))


def complement_uplift(static: np.ndarray, hazard_index: float, parameter: float) -> np.ndarray:
    """Bounded monotonic uplift: 1 - (1-static)*exp(-parameter*index)."""
    return 1.0 - (1.0 - static) * np.exp(-parameter * hazard_index)


FUSION_METHODS: dict[str, dict[str, Any]] = {
    "multiplicative_modulation": {
        "formula": "clip(staticSusceptibility * (1 + parameter * relativeHazardIndex), 0, 1)",
        "function": multiplicative_modulation,
        "assumptions": [
            "The multiplier is a policy sensitivity, not a probability product.",
            "Upper clipping can create ties and is treated as a potential saturation failure.",
        ],
    },
    "logit_shift": {
        "formula": "sigmoid(logit(staticSusceptibility) + parameter * relativeHazardIndex)",
        "function": logit_shift,
        "assumptions": [
            "The bounded output remains an uncalibrated scenario-conditioned score.",
            "A common log-odds shift strictly preserves static road ordering away from numerical limits.",
        ],
    },
    "complement_uplift": {
        "formula": "1 - (1 - staticSusceptibility) * exp(-parameter * relativeHazardIndex)",
        "function": complement_uplift,
        "assumptions": [
            "Hazard reduces the remaining distance to the upper score bound.",
            "The transform is bounded and order-preserving but can compress spatial contrast at high parameters.",
        ],
    },
}


def apply_fusion(method: str, static: np.ndarray, hazard_index: float, parameter: float) -> np.ndarray:
    function: Callable[[np.ndarray, float, float], np.ndarray] = FUSION_METHODS[method]["function"]
    values = np.asarray(function(np.asarray(static, dtype=np.float64), hazard_index, parameter), dtype=np.float64)
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError(f"Invalid fused output for {method} parameter={parameter}.")
    return values


def _strict_order_preserved(static: np.ndarray, dynamic: np.ndarray) -> bool:
    order = np.argsort(static, kind="stable")
    sorted_static = static[order]
    sorted_dynamic = dynamic[order]
    boundaries = np.flatnonzero(np.diff(sorted_static) > 0)
    return bool(all(sorted_dynamic[index] < sorted_dynamic[index + 1] for index in boundaries))


def _shift_report(lower: np.ndarray, upper: np.ndarray, thresholds: dict[str, float]) -> dict[str, Any]:
    difference = np.asarray(upper - lower, dtype=np.float64)
    lower_category = _risk_level(lower, thresholds)
    upper_category = _risk_level(upper, thresholds)
    return {
        "mean": _finite_float(difference.mean()),
        "median": _finite_float(np.median(difference)),
        "maximum": _finite_float(difference.max()),
        "absoluteAtLeast005": int(np.count_nonzero(np.abs(difference) >= 0.05)),
        "absoluteAtLeast010": int(np.count_nonzero(np.abs(difference) >= 0.10)),
        "absoluteAtLeast020": int(np.count_nonzero(np.abs(difference) >= 0.20)),
        "categoryChanged": int(np.count_nonzero(lower_category != upper_category)),
    }


def _road_inventory() -> tuple[list[dict[str, Any]], np.ndarray, dict[str, float], dict[str, Any]]:
    road_artifact = joblib.load(ROAD_MODEL_PATH)
    thresholds = {key: float(value) for key, value in road_artifact["riskThresholds"].items()}
    features = get_road_features().get("features", [])
    if len(features) != EXPECTED_ROAD_COUNT:
        raise ValueError(f"Expected {EXPECTED_ROAD_COUNT} computational roads, found {len(features)}.")
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(features):
        properties = feature["properties"]
        result = predict_risk(properties)
        rows.append(
            {
                "segmentId": str(properties["segmentId"]),
                "osmWayIds": [str(value) for value in properties.get("osmWayIds", [])],
                "geometryReference": f"app/data/roads/jakarta-2025-03-04-road-features.geojson#feature-{index}",
                "staticSusceptibility": float(result.riskProbability),
                "existingRiskLevel": result.riskLevel,
            }
        )
    ids = [row["segmentId"] for row in rows]
    if len(set(ids)) != EXPECTED_ROAD_COUNT:
        raise ValueError("Computational road segment IDs must be unique.")
    scores = np.asarray([row["staticSusceptibility"] for row in rows], dtype=np.float64)
    metadata = {
        "count": len(rows),
        "segmentIdSha256": _sha256_text(ids),
        "uniqueScoreCount": int(len(np.unique(scores))),
        "duplicateScoreCount": int(len(scores) - len(np.unique(scores))),
        "osmWayReferenceCount": int(sum(len(row["osmWayIds"]) for row in rows)),
        "distribution": _distribution(scores),
        "existingCategoryCounts": _category_counts(scores, thresholds),
    }
    return rows, scores, thresholds, metadata


def _temporal_scenarios() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if file_sha256(TEMPORAL_MODEL_PATH) != EXPECTED_TEMPORAL_MODEL_SHA256:
        raise ValueError("Frozen Phase 2 temporal model hash mismatch.")
    phase3a = json.loads(PHASE3A_ANALYSIS_PATH.read_text(encoding="utf-8"))
    if phase3a.get("decisionGate") != "GO" or phase3a["dataGovernance"].get("testAccessed"):
        raise ValueError("Phase 3A provenance or decision gate is unsuitable for fusion research.")
    temporal_model = load_frozen_model(TEMPORAL_MODEL_PATH)
    train = load_split("train")
    train_scores = temporal_model.predict_proba(train)
    representatives = {row["membership"]: row for row in phase3a["representatives"]}
    scenarios = []
    with np.load(REPRESENTATIVES_PATH, allow_pickle=False) as payload:
        for group in phase3a["quantileMethod"]["trainGroups"]:
            scenario_id = group["id"]
            representative = representatives[f"quantile_{scenario_id}"]
            sequence = payload[f"quantile_{scenario_id}"]
            score = float(group["hazardScoreMedian"])
            scenarios.append(
                {
                    "id": scenario_id,
                    "scenarioTemporalHazardScore": score,
                    "scoreAggregation": "median frozen-model score within the train-derived quantile group",
                    "relativeHazardIndex": empirical_percentile_rank(train_scores, score),
                    "representativeTemporalHazardScore": float(representative["temporalHazardScore"]),
                    "representativeTrainSampleIndex": int(representative["sourceSampleIndex"]),
                    "referenceDate": representative["referenceDate"],
                    "sequenceShape": list(sequence.shape),
                    "sequenceSha256": hashlib.sha256(sequence.tobytes(order="C")).hexdigest(),
                    "sequenceArtifact": "artifacts/dynamic-hazard/experiments/phase3a/representative_sequences.npz",
                    "sourceSplit": "train-2014-2018",
                }
            )
    indices = [row["relativeHazardIndex"] for row in scenarios]
    if not all(lower < upper for lower, upper in zip(indices, indices[1:], strict=False)):
        raise ValueError("Q1-Q4 relative hazard indices must be strictly increasing.")
    provenance = {
        "normalization": "mid-rank empirical percentile within frozen temporalHazardScore values on train",
        "fitSplit": "train-2014-2018",
        "trainSampleCount": int(len(train_scores)),
        "trainScoreDistribution": _distribution(train_scores),
        "validationAccessedForNormalization": False,
        "testAccessed": False,
        "bounded": True,
        "monotonic": True,
    }
    return scenarios, provenance


def _od_pairs() -> list[tuple[str, str]]:
    graph = get_routing_graph()
    paths = graph.get("metadata", {}).get("selectedPaths", [])
    return sorted({(row["originFacilityId"], row["destinationFacilityId"]) for row in paths})


def _routing_snapshot(road_rows: list[dict[str, Any]], dynamic: np.ndarray) -> dict[str, Any]:
    mapping = {
        row["segmentId"]: {
            # Legacy routing input field used as an offline adapter only. Its value is dynamicRoadRiskScore.
            "riskProbability": float(value),
            "riskLevel": row["dynamicRiskLevel"],
        }
        for row, value in zip(road_rows, dynamic, strict=True)
    }
    paths = []
    unreachable = 0
    changed = 0
    for origin, destination in _od_pairs():
        routes = calculate_routes(origin, destination, mapping)
        if not routes:
            unreachable += 1
            paths.append({"origin": origin, "destination": destination, "unreachable": True})
            continue
        baseline = routes[0]
        selected = routes[-1]
        changed_from_baseline = selected.affected_road_segment_ids != baseline.affected_road_segment_ids
        changed += int(changed_from_baseline)
        selected_values = np.asarray(
            [mapping[segment]["riskProbability"] for segment in selected.affected_road_segment_ids], dtype=np.float64
        )
        paths.append(
            {
                "origin": origin,
                "destination": destination,
                "unreachable": False,
                "changedFromBaseline": changed_from_baseline,
                "baselinePathSha256": _sha256_text(baseline.affected_road_segment_ids),
                "selectedPathSha256": _sha256_text(selected.affected_road_segment_ids),
                "baselineSegmentCount": len(baseline.affected_road_segment_ids),
                "selectedSegmentCount": len(selected.affected_road_segment_ids),
                "baselineTravelTimeMinutes": baseline.eta_minutes,
                "selectedTravelTimeMinutes": selected.eta_minutes,
                "travelTimeChangeMinutes": selected.eta_minutes - baseline.eta_minutes,
                "selectedMaximumDynamicRoadRiskScore": _finite_float(selected_values.max()),
                "selectedMeanDynamicRoadRiskScore": _finite_float(selected_values.mean()),
                "selectedRiskLevel": selected.flood_exposure,
            }
        )
    reachable = [row for row in paths if not row["unreachable"]]
    return {
        "odPairCount": len(paths),
        "unreachableCount": unreachable,
        "changedFromBaselineCount": changed,
        "meanSelectedTravelTimeMinutes": _finite_float(
            np.mean([row["selectedTravelTimeMinutes"] for row in reachable])
        ),
        "meanTravelTimeChangeMinutes": _finite_float(np.mean([row["travelTimeChangeMinutes"] for row in reachable])),
        "meanSelectedMaximumDynamicRoadRiskScore": _finite_float(
            np.mean([row["selectedMaximumDynamicRoadRiskScore"] for row in reachable])
        ),
        "paths": paths,
    }


def _routing_transition(lower: dict[str, Any], upper: dict[str, Any]) -> dict[str, Any]:
    lower_paths = {(row["origin"], row["destination"]): row for row in lower["paths"]}
    upper_paths = {(row["origin"], row["destination"]): row for row in upper["paths"]}
    changed = 0
    risk_changes = []
    travel_changes = []
    for pair, low in lower_paths.items():
        high = upper_paths[pair]
        if low.get("unreachable") or high.get("unreachable"):
            continue
        changed += int(low["selectedPathSha256"] != high["selectedPathSha256"])
        risk_changes.append(high["selectedMaximumDynamicRoadRiskScore"] - low["selectedMaximumDynamicRoadRiskScore"])
        travel_changes.append(high["selectedTravelTimeMinutes"] - low["selectedTravelTimeMinutes"])
    return {
        "changedOdPathCount": changed,
        "meanMaximumRiskChange": _finite_float(np.mean(risk_changes)),
        "meanTravelTimeChangeMinutes": _finite_float(np.mean(travel_changes)),
    }


def _evaluate_candidate(
    method: str,
    parameter: float,
    static: np.ndarray,
    scenarios: list[dict[str, Any]],
    thresholds: dict[str, float],
    road_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, np.ndarray]]:
    outputs: dict[str, np.ndarray] = {}
    scenario_rows = []
    routing_rows: dict[str, Any] = {}
    for scenario in scenarios:
        scenario_id = scenario["id"]
        dynamic = apply_fusion(method, static, scenario["relativeHazardIndex"], parameter)
        outputs[scenario_id] = dynamic
        categories = _risk_level(dynamic, thresholds)
        for row, level in zip(road_rows, categories, strict=True):
            row["dynamicRiskLevel"] = str(level)
        routing_rows[scenario_id] = _routing_snapshot(road_rows, dynamic)
        correlation = spearmanr(static, dynamic).statistic
        scenario_rows.append(
            {
                "scenario": scenario_id,
                "distribution": _distribution(dynamic),
                "categoryCounts": _category_counts(dynamic, thresholds),
                "staticSpearmanCorrelation": _finite_float(correlation),
                "strictSpatialOrderingPreserved": _strict_order_preserved(static, dynamic),
                "fractionAtOrBelow001": _finite_float(np.mean(dynamic <= 0.01)),
                "fractionAtOrAbove099": _finite_float(np.mean(dynamic >= 0.99)),
                "routing": routing_rows[scenario_id],
            }
        )
    shifts = {
        name: _shift_report(outputs[lower], outputs[upper], thresholds)
        for name, lower, upper in (
            ("Q1_to_Q2", "Q1", "Q2"),
            ("Q2_to_Q3", "Q2", "Q3"),
            ("Q3_to_Q4", "Q3", "Q4"),
            ("Q1_to_Q4", "Q1", "Q4"),
        )
    }
    routing_transitions = {
        name: _routing_transition(routing_rows[lower], routing_rows[upper])
        for name, lower, upper in (
            ("Q1_to_Q2", "Q1", "Q2"),
            ("Q2_to_Q3", "Q2", "Q3"),
            ("Q3_to_Q4", "Q3", "Q4"),
            ("Q1_to_Q4", "Q1", "Q4"),
        )
    }
    matrix = np.vstack([outputs[key] for key in SCENARIO_IDS])
    q1 = scenario_rows[0]
    q4 = scenario_rows[-1]
    invariants = {
        "monotonicScenarioEffect": bool(np.all(np.diff(matrix, axis=0) >= -1e-12)),
        "strictSpatialOrderingPreserved": all(row["strictSpatialOrderingPreserved"] for row in scenario_rows),
        "noScenarioCollapse": shifts["Q1_to_Q4"]["median"] >= 0.05,
        "noSaturationCollapse": q1["fractionAtOrBelow001"] < 0.05 and q4["fractionAtOrAbove099"] < 0.05,
        "deterministicByConstruction": True,
    }
    record = {
        "method": method,
        "parameter": parameter,
        "scenarioResults": scenario_rows,
        "scoreShifts": shifts,
        "routingTransitions": routing_transitions,
        "invariants": invariants,
    }
    return record, scenario_rows, outputs


def _select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = []
    for row in candidates:
        invariants = row["invariants"]
        shift = row["scoreShifts"]["Q1_to_Q4"]
        routing = row["routingTransitions"]["Q1_to_Q4"]
        if (
            all(invariants.values())
            and shift["absoluteAtLeast005"] >= round(0.25 * EXPECTED_ROAD_COUNT)
            and shift["categoryChanged"] > 0
            and routing["changedOdPathCount"] >= math.ceil(0.25 * len(_od_pairs()))
        ):
            eligible.append(row)
    family_order = {"logit_shift": 0, "complement_uplift": 1, "multiplicative_modulation": 2}
    if not eligible:
        raise RuntimeError("No fusion candidate passed the conservative research selection gate.")
    # Prefer the most defensible family, then the smallest policy parameter that propagates to routing.
    return min(eligible, key=lambda row: (family_order[row["method"]], row["parameter"]))


def _write_comparison(path: Path, candidates: list[dict[str, Any]]) -> None:
    fields = [
        "method",
        "parameter",
        "scenario",
        "minimum",
        "p25",
        "median",
        "mean",
        "p75",
        "p90",
        "p95",
        "maximum",
        "variance",
        "low",
        "medium",
        "high",
        "critical",
        "staticSpearmanCorrelation",
        "changedFromBaselineOdPaths",
    ]
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            for scenario in candidate["scenarioResults"]:
                writer.writerow(
                    {
                        "method": candidate["method"],
                        "parameter": candidate["parameter"],
                        "scenario": scenario["scenario"],
                        **scenario["distribution"],
                        **scenario["categoryCounts"],
                        "staticSpearmanCorrelation": scenario["staticSpearmanCorrelation"],
                        "changedFromBaselineOdPaths": scenario["routing"]["changedFromBaselineCount"],
                    }
                )


def _write_selected_roads(
    path: Path,
    road_rows: list[dict[str, Any]],
    selected: dict[str, Any],
    selected_outputs: dict[str, np.ndarray],
) -> None:
    fields = [
        "segmentId",
        "osmWayIds",
        "geometryReference",
        "staticSusceptibility",
        "existingRiskLevel",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
    ]
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(road_rows):
            writer.writerow(
                {
                    "segmentId": row["segmentId"],
                    "osmWayIds": "|".join(row["osmWayIds"]),
                    "geometryReference": row["geometryReference"],
                    "staticSusceptibility": row["staticSusceptibility"],
                    "existingRiskLevel": row["existingRiskLevel"],
                    **{scenario: float(selected_outputs[scenario][index]) for scenario in SCENARIO_IDS},
                }
            )


def run_analysis(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tracked_inputs = [ROAD_FEATURES_PATH, ROUTING_GRAPH_PATH, ROAD_MODEL_PATH, TEMPORAL_MODEL_PATH]
    input_hashes_before = {str(path.relative_to(BE_DIR)): file_sha256(path) for path in tracked_inputs}
    if input_hashes_before[str(ROAD_MODEL_PATH.relative_to(BE_DIR))] != EXPECTED_ROAD_MODEL_SHA256:
        raise ValueError("Frozen road susceptibility model hash mismatch.")

    road_rows, static, thresholds, road_metadata = _road_inventory()
    scenarios, normalization = _temporal_scenarios()
    candidates = []
    candidate_outputs: dict[tuple[str, float], dict[str, np.ndarray]] = {}
    for method in FUSION_METHODS:
        for parameter in PARAMETERS:
            record, _, outputs = _evaluate_candidate(method, parameter, static, scenarios, thresholds, road_rows)
            candidates.append(record)
            candidate_outputs[(method, parameter)] = outputs

    selected = _select_candidate(candidates)
    selected_outputs = candidate_outputs[(selected["method"], selected["parameter"])]
    input_hashes_after = {str(path.relative_to(BE_DIR)): file_sha256(path) for path in tracked_inputs}
    if input_hashes_before != input_hashes_after:
        raise RuntimeError("Research routing mutated a frozen runtime input.")

    analysis = {
        "analysisVersion": "dynamic-hazard-phase3b-v1",
        "researchOnly": True,
        "probabilityCalibrated": False,
        "outputSemantics": "dynamicRoadRiskScore is a scenario-conditioned relative road-risk score",
        "roadSusceptibility": {
            **road_metadata,
            "modelVersion": str(joblib.load(ROAD_MODEL_PATH)["version"]),
            "modelSha256": EXPECTED_ROAD_MODEL_SHA256,
            "riskThresholdsUnmodified": thresholds,
            "sourceFeatureArtifact": str(ROAD_FEATURES_PATH.relative_to(BE_DIR)).replace("\\", "/"),
        },
        "temporalScenarios": scenarios,
        "relativeHazardIndex": normalization,
        "fusionMethods": [
            {
                "method": name,
                "formula": details["formula"],
                "parameters": list(PARAMETERS),
                "assumptions": details["assumptions"],
            }
            for name, details in FUSION_METHODS.items()
        ],
        "parameterGovernance": "policy/sensitivity calibrated; not fitted to supervised road-level dynamic labels",
        "candidates": candidates,
        "selectedCandidate": {"method": selected["method"], "parameter": selected["parameter"]},
        "selectionRule": (
            "Require all invariants, >=25% of roads shifting by 0.05, category movement, and Q1-to-Q4 "
            "NetworkX path changes for >=25% of existing OD pairs; prefer logit shift, then the smallest "
            "passing policy parameter."
        ),
        "runtimeMutationCheck": {
            "inputsBefore": input_hashes_before,
            "inputsAfter": input_hashes_after,
            "unchanged": input_hashes_before == input_hashes_after,
        },
        "limitations": [
            "No road-level dynamic flood ground truth exists; fusion strength is not accuracy-fitted.",
            "Both input models are frozen and represent different targets.",
            "The output is not a calibrated probability, road flood forecast, or closure forecast.",
            (
                "Temporal scenarios are Jakarta-wide and contain transformed source features without physical "
                "rainfall units."
            ),
            (
                "Current category thresholds were designed for the static model and are only reused for "
                "sensitivity analysis."
            ),
            "Routing sensitivity covers the 12 facility OD pairs encoded in the existing Jakarta graph snapshot.",
        ],
    }
    routing_artifact = {
        "analysisVersion": analysis["analysisVersion"],
        "researchOnly": True,
        "legacyAdapterNote": (
            "calculate_routes receives dynamicRoadRiskScore through its existing riskProbability key only as an "
            "offline adapter; this does not confer probability semantics."
        ),
        "odPairs": [{"origin": origin, "destination": destination} for origin, destination in _od_pairs()],
        "candidates": [
            {
                "method": row["method"],
                "parameter": row["parameter"],
                "scenarios": {scenario["scenario"]: scenario["routing"] for scenario in row["scenarioResults"]},
                "transitions": row["routingTransitions"],
            }
            for row in candidates
        ],
    }
    selected_record = {
        "method": selected["method"],
        "parameter": selected["parameter"],
        "temporalInput": "relativeHazardIndex",
        "spatialInput": "existing road susceptibility",
        "output": "dynamicRoadRiskScore",
        "probabilityCalibrated": False,
        "runtimeConfiguration": False,
        "parameterGovernance": analysis["parameterGovernance"],
        "selectionBasis": [
            "all five fusion invariants passed",
            "strict spatial ordering preserved",
            "Q1-to-Q4 road-score movement was material",
            "at least 25% of existing NetworkX OD paths responded to Q1-to-Q4 escalation",
            "preferred explainable bounded logit-shift family when eligible",
            "smallest passing policy parameter within the preferred family",
        ],
        "limitations": analysis["limitations"],
        "sourceAnalysisSha256": _json_sha256(analysis),
    }
    save_json(output_dir / "fusion_analysis.json", analysis)
    save_json(output_dir / "routing_sensitivity.json", routing_artifact)
    save_json(output_dir / "selected_fusion.json", selected_record)
    _write_comparison(output_dir / "fusion_comparison.csv", candidates)
    _write_selected_roads(output_dir / "selected_road_scores.csv", road_rows, selected, selected_outputs)
    return {
        "analysis": analysis,
        "routing": routing_artifact,
        "selected": selected_record,
        "selectedOutputs": selected_outputs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate offline temporal-hazard and road-susceptibility fusion.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_analysis(args.output_dir)
    print(json.dumps(result["selected"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
