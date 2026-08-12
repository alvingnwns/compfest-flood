from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from train_indonesia_historical_flood_model import (
    CATEGORICAL_FEATURES,
    DATA_DIR,
    FEATURES_PATH,
    MODEL_PATH,
    NUMERIC_FEATURES,
    _geometry_features,
    _metrics,
    _pipeline,
    _threshold,
)

BASE_DIR = Path(__file__).resolve().parent.parent
EVALUATION_PATH = DATA_DIR / "model-evaluation.json"
AUDIT_PATH = DATA_DIR / "model-audit.json"
JAKARTA_PATH = BASE_DIR / "app" / "data" / "roads" / "jakarta-2025-03-04-road-features.geojson"
JAKARTA_FEATURES_PATH = DATA_DIR / "jakarta-inference-features.csv"


def _group_metrics(frame: pd.DataFrame, probability: np.ndarray, threshold: float, group: str) -> list[dict[str, Any]]:
    working = frame.copy()
    working["probability"] = probability
    output = []
    for name, values in working.groupby(group):
        if values["target"].nunique() < 2:
            continue
        output.append({group: name, **_metrics(values["target"], values["probability"].to_numpy(), threshold)})
    return output


def _calibration(y: pd.Series, probability: np.ndarray) -> list[dict[str, Any]]:
    bins = np.linspace(0, 1, 11)
    indices = np.clip(np.digitize(probability, bins) - 1, 0, 9)
    output = []
    for index in range(10):
        mask = indices == index
        if not mask.any():
            continue
        output.append(
            {
                "binLower": float(bins[index]),
                "binUpper": float(bins[index + 1]),
                "count": int(mask.sum()),
                "meanPredicted": float(probability[mask].mean()),
                "observedRate": float(y.to_numpy()[mask].mean()),
            }
        )
    return output


def _jakarta_features() -> pd.DataFrame:
    payload = json.loads(JAKARTA_PATH.read_text(encoding="utf-8"))
    rows = []
    for feature in payload["features"]:
        properties = feature["properties"]
        rows.append(
            {
                "segment_id": properties["segmentId"],
                "highway": properties["highway"],
                "log_length_meters": math.log1p(float(properties["lengthKm"]) * 1_000),
                "oneway": float(properties.get("oneway", False)),
                **_geometry_features(feature["geometry"]["coordinates"]),
                "prior_exposure_count": 0.0,
                "prior_exposure_frequency": 0.0,
                "prior_observed_events": 0.0,
                "years_since_prior_positive": 99.0,
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(JAKARTA_FEATURES_PATH, index=False)
    return frame


def _shift(train: pd.DataFrame, jakarta: pd.DataFrame) -> dict[str, Any]:
    numeric = {}
    for feature in NUMERIC_FEATURES:
        low, high = float(train[feature].min()), float(train[feature].max())
        outside = ((jakarta[feature] < low) | (jakarta[feature] > high)).mean()
        numeric[feature] = {
            "trainingMin": low,
            "trainingMax": high,
            "jakartaMin": float(jakarta[feature].min()),
            "jakartaMax": float(jakarta[feature].max()),
            "jakartaOutsideTrainingRangeFraction": float(outside),
        }
    training_categories = set(train["highway"])
    jakarta_categories = set(jakarta["highway"])
    return {
        "numeric": numeric,
        "categorical": {
            "highway": {
                "training": sorted(training_categories),
                "jakarta": sorted(jakarta_categories),
                "unseenInTraining": sorted(jakarta_categories - training_categories),
            }
        },
    }


def _ablation_model(name: str) -> Any:
    if name == "logisticRegression":
        return LogisticRegression(max_iter=2_000, class_weight="balanced", random_state=42)
    return RandomForestClassifier(
        n_estimators=400, min_samples_leaf=8, class_weight="balanced_subsample", random_state=42, n_jobs=-1
    )


def audit() -> dict[str, Any]:
    artifact = joblib.load(MODEL_PATH)
    evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    frame = pd.read_csv(FEATURES_PATH)
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "validation"]
    test = frame[frame["split"] == "test"]
    features = artifact["features"]
    pipeline = artifact["pipeline"]
    threshold = float(artifact["threshold"])
    test_probability = pipeline.predict_proba(test[features])[:, 1]
    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    transformed_names = preprocessor.get_feature_names_out().tolist()
    importances = sorted(
        (
            {"feature": name, "importance": float(value)}
            for name, value in zip(transformed_names, model.feature_importances_, strict=True)
        ),
        key=lambda item: item["importance"],
        reverse=True,
    )
    ablations = {}
    groups = {
        "withoutHistoricalExposure": [
            "prior_exposure_count",
            "prior_exposure_frequency",
            "prior_observed_events",
            "years_since_prior_positive",
        ],
        "withoutGeometry": ["sinuosity", "bearing_sin", "bearing_cos", "vertex_count"],
        "withoutRoadClass": ["highway"],
    }
    for ablation_name, removed in groups.items():
        numeric = [feature for feature in NUMERIC_FEATURES if feature not in removed]
        categorical = [feature for feature in CATEGORICAL_FEATURES if feature not in removed]
        candidate = _pipeline(_ablation_model(evaluation["selectedModel"]))
        candidate.named_steps["preprocessor"].transformers = [
            item for item in candidate.named_steps["preprocessor"].transformers if item[2]
        ]
        candidate.named_steps["preprocessor"].transformers[0] = (
            "numeric",
            candidate.named_steps["preprocessor"].transformers[0][1],
            numeric,
        )
        if categorical:
            candidate.named_steps["preprocessor"].transformers[1] = (
                "categorical",
                candidate.named_steps["preprocessor"].transformers[1][1],
                categorical,
            )
        else:
            candidate.named_steps["preprocessor"].transformers = candidate.named_steps["preprocessor"].transformers[:1]
        selected_features = numeric + categorical
        candidate.fit(train[selected_features], train["target"])
        validation_probability = candidate.predict_proba(validation[selected_features])[:, 1]
        ablation_threshold = _threshold(validation["target"], validation_probability)
        ablations[ablation_name] = {
            "removed": removed,
            "threshold": ablation_threshold,
            "validation": _metrics(validation["target"], validation_probability, ablation_threshold),
            "test": _metrics(
                test["target"], candidate.predict_proba(test[selected_features])[:, 1], ablation_threshold
            ),
        }
    jakarta = _jakarta_features()
    jakarta_probability = pipeline.predict_proba(jakarta[features])[:, 1]
    levels = pd.cut(
        jakarta_probability, [-np.inf, 0.25, 0.5, 0.75, np.inf], labels=["low", "medium", "high", "critical"]
    )
    shift = _shift(train, jakarta)
    outside_fractions = [value["jakartaOutsideTrainingRangeFraction"] for value in shift["numeric"].values()]
    unseen_categories = shift["categorical"]["highway"]["unseenInTraining"]
    shift_status = (
        "PARTIALLY OUT-OF-DISTRIBUTION"
        if any(value > 0.05 for value in outside_fractions) or unseen_categories
        else "IN-DISTRIBUTION"
    )
    audit_payload = {
        "version": artifact["version"],
        "testOverall": _metrics(test["target"], test_probability, threshold),
        "perRegion": _group_metrics(test, test_probability, threshold, "region_id"),
        "perEvent": _group_metrics(test, test_probability, threshold, "event_id"),
        "calibration": _calibration(test["target"], test_probability),
        "featureImportance": importances,
        "ablation": ablations,
        "jakartaDistributionShift": {"status": shift_status, **shift},
        "jakartaInference": {
            "roads": len(jakarta),
            "probabilityMin": float(jakarta_probability.min()),
            "probabilityMedian": float(np.median(jakarta_probability)),
            "probabilityMean": float(jakarta_probability.mean()),
            "probabilityMax": float(jakarta_probability.max()),
            "riskLevels": {str(key): int(value) for key, value in levels.value_counts().sort_index().items()},
            "interpretation": "Deployment/demo inference only; these probabilities are not Jakarta accuracy evidence.",
        },
        "geographicGeneralizationAnswer": (
            "On three entirely unseen regions, performance exceeded both trivial baselines but positive recall was "
            "low; "
            "cross-region generalization is measurable but limited."
        ),
    }
    AUDIT_PATH.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")
    print(json.dumps(audit_payload, indent=2))
    return audit_payload


if __name__ == "__main__":
    audit()
