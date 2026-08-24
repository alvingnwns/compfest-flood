from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from dynamic_hazard.analyze_road_risk_fusion import (
    EXPECTED_ROAD_COUNT,
    EXPECTED_ROAD_MODEL_SHA256,
    EXPECTED_TEMPORAL_MODEL_SHA256,
    ROAD_FEATURES_PATH,
    ROAD_MODEL_PATH,
    ROUTING_GRAPH_PATH,
    TEMPORAL_MODEL_PATH,
    apply_fusion,
    empirical_percentile_rank,
    run_analysis,
)
from dynamic_hazard.common import file_sha256

from app.repositories.geospatial_repository import get_road_features

BE_DIR = Path(__file__).resolve().parents[1]
PHASE3B_DIR = BE_DIR / "artifacts" / "dynamic-hazard" / "experiments" / "phase3b"


def _strict_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def test_frozen_provenance_and_train_only_normalization() -> None:
    analysis = _strict_json(PHASE3B_DIR / "fusion_analysis.json")
    assert file_sha256(TEMPORAL_MODEL_PATH) == EXPECTED_TEMPORAL_MODEL_SHA256
    assert file_sha256(ROAD_MODEL_PATH) == EXPECTED_ROAD_MODEL_SHA256
    assert analysis["roadSusceptibility"]["count"] == EXPECTED_ROAD_COUNT
    assert analysis["roadSusceptibility"]["modelSha256"] == EXPECTED_ROAD_MODEL_SHA256
    normalization = analysis["relativeHazardIndex"]
    assert normalization["fitSplit"] == "train-2014-2018"
    assert normalization["validationAccessedForNormalization"] is False
    assert normalization["testAccessed"] is False
    indices = [row["relativeHazardIndex"] for row in analysis["temporalScenarios"]]
    assert all(lower < upper for lower, upper in zip(indices, indices[1:], strict=False))
    assert empirical_percentile_rank(np.array([0.1, 0.2, 0.3]), 0.2) == pytest.approx(0.5)


def test_fusion_is_deterministic_bounded_monotonic_and_order_preserving() -> None:
    static = np.array([0.01, 0.2, 0.2, 0.8], dtype=np.float64)
    indices = [0.15, 0.46, 0.65, 0.73]
    for method in ("multiplicative_modulation", "logit_shift", "complement_uplift"):
        first = np.vstack([apply_fusion(method, static, index, 1.0) for index in indices])
        second = np.vstack([apply_fusion(method, static, index, 1.0) for index in indices])
        assert np.array_equal(first, second)
        assert np.isfinite(first).all()
        assert np.all((first >= 0) & (first <= 1))
        assert np.all(np.diff(first, axis=0) >= 0)
        assert np.all(np.diff(first[:, [0, 1, 3]], axis=1) > 0)


def test_selected_artifact_has_all_real_roads_and_required_invariants() -> None:
    analysis = _strict_json(PHASE3B_DIR / "fusion_analysis.json")
    selected = _strict_json(PHASE3B_DIR / "selected_fusion.json")
    assert selected["method"] == "logit_shift"
    assert selected["parameter"] == 1.5
    assert selected["probabilityCalibrated"] is False
    assert selected["runtimeConfiguration"] is False
    selected_candidate = next(
        row
        for row in analysis["candidates"]
        if row["method"] == selected["method"] and row["parameter"] == selected["parameter"]
    )
    assert all(selected_candidate["invariants"].values())
    assert selected_candidate["routingTransitions"]["Q1_to_Q4"]["changedOdPathCount"] >= 3

    expected_ids = {feature["properties"]["segmentId"] for feature in get_road_features()["features"]}
    with (PHASE3B_DIR / "selected_road_scores.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == EXPECTED_ROAD_COUNT
    assert {row["segmentId"] for row in rows} == expected_ids
    for row in rows:
        values = np.asarray([float(row[scenario]) for scenario in ("Q1", "Q2", "Q3", "Q4")])
        assert np.isfinite(values).all()
        assert np.all((values >= 0) & (values <= 1))
        assert np.all(np.diff(values) >= 0)


def test_research_run_does_not_mutate_runtime_and_is_byte_reproducible(tmp_path: Path) -> None:
    runtime_paths = (ROAD_MODEL_PATH, ROAD_FEATURES_PATH, ROUTING_GRAPH_PATH)
    before = {path: file_sha256(path) for path in runtime_paths}
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    run_analysis(first_dir)
    run_analysis(second_dir)
    after = {path: file_sha256(path) for path in runtime_paths}
    assert before == after
    expected_files = {
        "fusion_analysis.json",
        "fusion_comparison.csv",
        "routing_sensitivity.json",
        "selected_fusion.json",
        "selected_road_scores.csv",
    }
    assert {path.name for path in first_dir.iterdir()} == expected_files
    for name in expected_files:
        first_hash = hashlib.sha256((first_dir / name).read_bytes()).hexdigest()
        second_hash = hashlib.sha256((second_dir / name).read_bytes()).hexdigest()
        assert first_hash == second_hash


def test_scientific_wording_and_strict_machine_readability() -> None:
    for name in ("fusion_analysis.json", "routing_sensitivity.json", "selected_fusion.json"):
        _strict_json(PHASE3B_DIR / name)
    serialized = (PHASE3B_DIR / "fusion_analysis.json").read_text(encoding="utf-8").lower()
    assert 'probabilitycalibrated": false' in serialized
    assert "dynamicroadriskscore" in serialized
    assert "probability this road will flood" not in serialized
    assert "real-time flood probability" not in serialized
