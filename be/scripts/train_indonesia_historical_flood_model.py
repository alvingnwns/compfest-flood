from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data" / "indonesia-flood-ml"
LABELS_PATH = DATA_DIR / "road-event-labels.csv"
ROADS_DIR = DATA_DIR / "roads"
FEATURES_PATH = DATA_DIR / "model-features.csv"
SPLIT_PATH = DATA_DIR / "dataset-split.json"
EVALUATION_PATH = DATA_DIR / "model-evaluation.json"
MODEL_PATH = BASE_DIR / "app" / "models" / "flood_risk_model.joblib"
METRICS_PATH = BASE_DIR / "app" / "models" / "flood_risk_metrics.json"
VERSION = "indonesia-road-corridor-flood-exposure-v1"
TEST_REGIONS = {"gaul2-73682", "gaul2-73814", "gaul2-73847"}
VALIDATION_START = "2012-01-01"
NUMERIC_FEATURES = [
    "log_length_meters",
    "oneway",
    "sinuosity",
    "bearing_sin",
    "bearing_cos",
    "vertex_count",
    "prior_exposure_count",
    "prior_exposure_frequency",
    "prior_observed_events",
    "years_since_prior_positive",
]
CATEGORICAL_FEATURES = ["highway"]


def _geometry_features(coordinates: list[list[float]]) -> dict[str, float]:
    start, end = coordinates[0], coordinates[-1]
    dx = (end[0] - start[0]) * math.cos(math.radians((start[1] + end[1]) / 2))
    dy = end[1] - start[1]
    chord = math.hypot(dx, dy) * 111_320
    path = 0.0
    for left, right in zip(coordinates, coordinates[1:], strict=False):
        path += (
            math.hypot((right[0] - left[0]) * math.cos(math.radians((left[1] + right[1]) / 2)), right[1] - left[1])
            * 111_320
        )
    bearing = math.atan2(dx, dy)
    return {
        "sinuosity": min(path / chord, 20.0) if chord > 1 else 1.0,
        "bearing_sin": math.sin(bearing),
        "bearing_cos": math.cos(bearing),
        "vertex_count": float(len(coordinates)),
    }


def build_features() -> pd.DataFrame:
    geometries = {}
    for path in ROADS_DIR.glob("*.geojson"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for feature in payload["features"]:
            geometries[feature["properties"]["segmentId"]] = _geometry_features(feature["geometry"]["coordinates"])
    with LABELS_PATH.open(encoding="utf-8", newline="") as source:
        rows = [row for row in csv.DictReader(source) if row["label"] in {"positive", "negative"}]
    rows.sort(key=lambda row: (row["event_start"], row["event_id"], row["region_id"], row["segment_id"]))
    history: dict[str, list[tuple[str, int]]] = defaultdict(list)
    output = []
    by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_event[row["event_id"]].append(row)
    for event_id in sorted(by_event, key=lambda key: (by_event[key][0]["event_start"], key)):
        event_rows = by_event[event_id]
        event_start = event_rows[0]["event_start"]
        year = int(event_start[:4])
        for row in event_rows:
            prior = history[row["segment_id"]]
            positives = [item for item in prior if item[1] == 1]
            years_since = year - int(positives[-1][0][:4]) if positives else 99.0
            output.append(
                {
                    "segment_id": row["segment_id"],
                    "event_id": event_id,
                    "event_start": event_start,
                    "region_id": row["region_id"],
                    "highway": row["highway"],
                    "log_length_meters": math.log1p(float(row["segment_length_meters"])),
                    "oneway": float(row["oneway"].lower() == "true"),
                    **geometries[row["segment_id"]],
                    "prior_exposure_count": float(len(positives)),
                    "prior_exposure_frequency": len(positives) / len(prior) if prior else 0.0,
                    "prior_observed_events": float(len(prior)),
                    "years_since_prior_positive": float(years_since),
                    "target": int(row["label"] == "positive"),
                }
            )
        for row in event_rows:
            history[row["segment_id"]].append((event_start, int(row["label"] == "positive")))
    frame = pd.DataFrame(output)
    frame["split"] = np.where(
        frame["region_id"].isin(TEST_REGIONS),
        "test",
        np.where(frame["event_start"] >= VALIDATION_START, "validation", "train"),
    )
    frame.to_csv(FEATURES_PATH, index=False)
    return frame


def _pipeline(model: Any) -> Pipeline:
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline(
        [("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]
    )
    return Pipeline(
        [
            (
                "preprocessor",
                ColumnTransformer(
                    [("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)]
                ),
            ),
            ("model", model),
        ]
    )


def _threshold(y: pd.Series, probability: np.ndarray) -> float:
    candidates = np.linspace(0.05, 0.95, 91)
    recall_floor = 0.7
    eligible = [value for value in candidates if recall_score(y, probability >= value) >= recall_floor]
    search = eligible or candidates
    return float(
        max(search, key=lambda value: (f1_score(y, probability >= value), precision_score(y, probability >= value)))
    )


def _metrics(y: pd.Series, probability: np.ndarray, threshold: float) -> dict[str, Any]:
    prediction = probability >= threshold
    return {
        "precision": precision_score(y, prediction, zero_division=0),
        "recall": recall_score(y, prediction, zero_division=0),
        "f1": f1_score(y, prediction, zero_division=0),
        "rocAuc": roc_auc_score(y, probability),
        "prAuc": average_precision_score(y, probability),
        "brier": brier_score_loss(y, probability),
        "confusionMatrix": confusion_matrix(y, prediction).tolist(),
        "support": len(y),
        "positive": int(y.sum()),
    }


def train() -> dict[str, Any]:
    frame = build_features()
    feature_columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    splits = {name: frame[frame["split"] == name] for name in ("train", "validation", "test")}
    for name, split in splits.items():
        if split["target"].nunique() != 2:
            raise RuntimeError(f"Split {name} lacks both classes")
    candidates = {
        "logisticRegression": _pipeline(LogisticRegression(max_iter=2_000, class_weight="balanced", random_state=42)),
        "randomForest": _pipeline(
            RandomForestClassifier(
                n_estimators=400, min_samples_leaf=8, class_weight="balanced_subsample", random_state=42, n_jobs=-1
            )
        ),
    }
    results = {}
    fitted = {}
    for name, pipeline in candidates.items():
        pipeline.fit(splits["train"][feature_columns], splits["train"]["target"])
        validation_probability = pipeline.predict_proba(splits["validation"][feature_columns])[:, 1]
        threshold = _threshold(splits["validation"]["target"], validation_probability)
        fitted[name] = pipeline
        results[name] = {
            "threshold": threshold,
            "validation": _metrics(splits["validation"]["target"], validation_probability, threshold),
            "test": _metrics(
                splits["test"]["target"], pipeline.predict_proba(splits["test"][feature_columns])[:, 1], threshold
            ),
        }
    selected_name = max(
        results,
        key=lambda name: (
            results[name]["validation"]["prAuc"],
            results[name]["validation"]["f1"],
            results[name]["validation"]["recall"],
            -results[name]["validation"]["brier"],
        ),
    )
    selected = fitted[selected_name]
    threshold = results[selected_name]["threshold"]
    majority_probability = np.zeros(len(splits["test"]))
    history_probability = splits["test"]["prior_exposure_frequency"].to_numpy()
    baselines = {
        "majorityNegative": _metrics(splits["test"]["target"], majority_probability, 0.5),
        "causalHistoricalFrequency": _metrics(splits["test"]["target"], history_probability, threshold),
    }
    split_payload = {
        name: {
            "rows": len(split),
            "positive": int(split["target"].sum()),
            "events": sorted(split["event_id"].unique().tolist()),
            "regions": sorted(split["region_id"].unique().tolist()),
        }
        for name, split in splits.items()
    }
    SPLIT_PATH.write_text(json.dumps(split_payload, indent=2), encoding="utf-8")
    evaluation = {
        "version": VERSION,
        "trainingData": "real-historical-global-flood-database-indonesia",
        "selectedModel": selected_name,
        "selectionPolicy": (
            "Algorithm and threshold selected from validation only; final held-out-region test metrics were "
            "not used for tuning. Threshold maximizes validation F1 subject to recall >= 0.70 when feasible."
        ),
        "models": results,
        "baselines": baselines,
        "split": split_payload,
        "featureColumns": feature_columns,
        "prohibitedFeatures": [
            "region_id",
            "province",
            "latitude",
            "longitude",
            "same_event_flood_exposure",
            "same_event_quality",
            "event_duration",
            "event_severity",
        ],
    }
    EVALUATION_PATH.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    artifact = {
        "pipeline": selected,
        "features": feature_columns,
        "numericFeatures": NUMERIC_FEATURES,
        "categoricalFeatures": CATEGORICAL_FEATURES,
        "version": VERSION,
        "trainingData": "real-historical-global-flood-database-indonesia",
        "target": "roadCorridorFloodExposure",
        "threshold": threshold,
        "riskThresholds": {"low": 0.25, "medium": 0.5, "high": 0.75},
        "split": split_payload,
        "metrics": results[selected_name],
        "scikitLearnVersion": sklearn.__version__,
    }
    joblib.dump(artifact, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(json.dumps(evaluation, indent=2))
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Indonesia historical road-corridor flood models.")
    parser.parse_args()
    train()


if __name__ == "__main__":
    main()
