from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from pydantic import BaseModel

from app.errors import ApiError

APP_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = APP_DIR / "models" / "flood_risk_model.joblib"
JAKARTA_FEATURES_PATH = APP_DIR / "data" / "indonesia-flood-ml" / "jakarta-inference-features.csv"
EXPECTED_TRAINING_DATA = "real-historical-global-flood-database-indonesia"


class RiskResult(BaseModel):
    riskProbability: float
    riskLevel: str
    estimatedDelayMinutes: int
    riskFactors: list[dict[str, str]]


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise ApiError(500, "model_missing", "Artefak model risiko banjir historis tidak ditemukan.")
    artifact = joblib.load(MODEL_PATH)
    if artifact.get("trainingData") != EXPECTED_TRAINING_DATA or "pipeline" not in artifact:
        raise ApiError(500, "model_provenance_invalid", "Provenance model risiko banjir historis tidak valid.")
    return artifact


@lru_cache(maxsize=1)
def _jakarta_features() -> pd.DataFrame:
    if not JAKARTA_FEATURES_PATH.exists():
        raise ApiError(500, "features_missing", "Fitur lokal Jakarta untuk model historis tidak ditemukan.")
    frame = pd.read_csv(JAKARTA_FEATURES_PATH).set_index("segment_id", drop=False)
    if frame.index.has_duplicates:
        raise ApiError(500, "features_invalid", "ID segmen fitur model historis Jakarta tidak unik.")
    return frame


@lru_cache(maxsize=1)
def _jakarta_probabilities() -> pd.Series:
    artifact = _load_model()
    features = _jakarta_features()
    values = artifact["pipeline"].predict_proba(features[artifact["features"]])[:, 1]
    return pd.Series(values, index=features.index)


def warm_model() -> None:
    _jakarta_probabilities()


def model_version() -> str:
    return str(_load_model()["version"])


def model_provenance() -> dict[str, Any]:
    artifact = _load_model()
    split = artifact["split"]
    event_ids = {event for group in split.values() for event in group["events"]}
    region_ids = {region for group in split.values() for region in group["regions"]}
    algorithm = type(artifact["pipeline"].named_steps["model"]).__name__
    return {
        "training_data": artifact["trainingData"],
        "source": "Global Flood Database / MODIS_EVENTS/V1",
        "target": artifact["target"],
        "algorithm": algorithm,
        "training_scope": "32 kejadian banjir historis di 13 region Indonesia",
        "deployment_scope": "Jakarta sebagai pilot inferensi/demo",
        "training_events": len(event_ids),
        "training_regions": len(region_ids),
        "jakarta_validation_status": "not_validated",
        "probability_semantics": "Probabilitas paparan banjir koridor jalan, bukan kepastian jalan ditutup",
    }


def _risk_factors(row: pd.Series) -> list[dict[str, str]]:
    factors = [{"id": "road_class", "label": f"Kelas jalan OSM: {row['highway']}"}]
    if float(row["log_length_meters"]) >= 6:
        factors.append({"id": "segment_length", "label": "Segmen jalan OSM lebih panjang"})
    if float(row["sinuosity"]) >= 1.25:
        factors.append({"id": "road_geometry", "label": "Geometri segmen OSM berkelok"})
    if float(row["prior_observed_events"]) > 0:
        factors.append(
            {
                "id": "causal_history",
                "label": "Riwayat paparan koridor dari observasi satelit sebelumnya",
            }
        )
    else:
        factors.append(
            {
                "id": "no_local_label_history",
                "label": "Belum ada event Jakarta berlabel defensible; inferensi memakai fitur jalan statis",
            }
        )
    return factors


def predict_risk(road_properties: dict[str, Any]) -> RiskResult:
    artifact = _load_model()
    segment_id = str(road_properties.get("segmentId", ""))
    features = _jakarta_features()
    if segment_id not in features.index:
        raise ApiError(
            500,
            "segment_features_missing",
            "Fitur model historis tidak tersedia untuk segmen OSM Jakarta yang diminta.",
            details={"segmentId": segment_id},
        )
    row = features.loc[segment_id]
    probability = float(_jakarta_probabilities().loc[segment_id])
    thresholds = artifact["riskThresholds"]
    if probability < thresholds["low"]:
        level = "low"
    elif probability < thresholds["medium"]:
        level = "medium"
    elif probability < thresholds["high"]:
        level = "high"
    else:
        level = "critical"
    base_time = float(road_properties.get("travelTimeMinutes", 10))
    delay = round(base_time * probability * (3.5 if level == "critical" else 2))
    return RiskResult(
        riskProbability=round(probability, 4),
        riskLevel=level,
        estimatedDelayMinutes=delay,
        riskFactors=_risk_factors(row),
    )
