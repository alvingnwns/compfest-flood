from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "app" / "data" / "indonesia-flood-ml"
MODEL_PATH = BASE_DIR / "app" / "models" / "flood_risk_model.joblib"


def test_region_discovery_schema_and_selection_is_prelabel() -> None:
    discovery = json.loads((DATA_DIR / "region-discovery.json").read_text(encoding="utf-8"))
    assert discovery["metadata"]["collectionId"] == "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
    assert discovery["metadata"]["selectionTiming"].endswith("road-corridor labels.")
    assert discovery["summary"]["selectedEventRegionGroups"] == 32
    assert all(row["selectedForRoadPreparation"] for row in discovery["selected"])


def test_real_osm_road_ids_are_unique_across_regions() -> None:
    identifiers = []
    for path in (DATA_DIR / "roads").glob("*.geojson"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for feature in payload["features"]:
            properties = feature["properties"]
            identifiers.append(properties["segmentId"])
            assert properties["segmentId"].startswith(f"osm-{properties['regionId']}-")
            assert properties["osmWayIds"]
    assert len(identifiers) == len(set(identifiers)) == 13_771


def test_label_quality_and_unknowns_are_preserved() -> None:
    with (DATA_DIR / "road-event-labels.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 31_531
    for row in rows:
        if row["label"] == "positive":
            assert float(row["flood_exposure_fraction"]) >= 0.05
            assert float(row["source_coverage_fraction"]) >= 0.8
            assert float(row["valid_observation_fraction"]) >= 0.8
            assert float(row["permanent_water_fraction"]) < 0.2
        elif row["label"] == "negative":
            assert float(row["flood_exposure_fraction"]) <= 0.001
            assert float(row["source_coverage_fraction"]) >= 0.8
            assert float(row["valid_observation_fraction"]) >= 0.8
        else:
            assert row["exclusion_reason"]
    assert sum(row["label"] == "unknown" for row in rows) == 2_401


def test_causal_history_and_group_splits_have_no_leakage() -> None:
    frame = pd.read_csv(DATA_DIR / "model-features.csv")
    first = frame.sort_values(["event_start", "event_id"]).groupby("segment_id", as_index=False).first()
    assert (first["prior_observed_events"] == 0).all()
    split = json.loads((DATA_DIR / "dataset-split.json").read_text(encoding="utf-8"))
    train_events, validation_events, test_events = (
        set(split[name]["events"]) for name in ("train", "validation", "test")
    )
    assert train_events.isdisjoint(validation_events | test_events)
    assert validation_events.isdisjoint(test_events)
    assert set(split["test"]["regions"]).isdisjoint(split["train"]["regions"])
    assert set(split["test"]["regions"]).isdisjoint(split["validation"]["regions"])


def test_historical_artifact_probability_and_jakarta_compatibility() -> None:
    artifact = joblib.load(MODEL_PATH)
    assert artifact["trainingData"] == "real-historical-global-flood-database-indonesia"
    assert artifact["target"] == "roadCorridorFloodExposure"
    jakarta = pd.read_csv(DATA_DIR / "jakarta-inference-features.csv")
    probability = artifact["pipeline"].predict_proba(jakarta[artifact["features"]])[:, 1]
    assert len(probability) == 1_413
    assert ((probability >= 0) & (probability <= 1)).all()


def test_gate_and_evaluation_are_persisted() -> None:
    gate = json.loads((DATA_DIR / "scientific-feasibility-gate.json").read_text(encoding="utf-8"))
    evaluation = json.loads((DATA_DIR / "model-evaluation.json").read_text(encoding="utf-8"))
    audit = json.loads((DATA_DIR / "model-audit.json").read_text(encoding="utf-8"))
    assert gate["status"] == "PASS" and all(item["passed"] for item in gate["checks"].values())
    assert evaluation["selectedModel"] == "randomForest"
    assert audit["jakartaDistributionShift"]["status"] == "PARTIALLY OUT-OF-DISTRIBUTION"
    assert audit["testOverall"]["prAuc"] > evaluation["baselines"]["causalHistoricalFrequency"]["prAuc"]
