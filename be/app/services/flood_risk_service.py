from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from pydantic import BaseModel

from app.errors import ApiError

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "flood_risk_model.joblib"


class RiskResult(BaseModel):
    riskProbability: float
    riskLevel: str
    estimatedDelayMinutes: int
    riskFactors: list[dict[str, str]]


@lru_cache(maxsize=1)
def _load_model() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise ApiError(500, "model_missing", "Flood-risk model artifact was not found.")
    return joblib.load(MODEL_PATH)


def warm_model() -> None:
    artifact = _load_model()
    sample = pd.DataFrame([{feature: 0.0 for feature in artifact["features"]}])
    artifact["model"].predict_proba(artifact["scaler"].transform(sample))


def predict_risk(road_properties: dict[str, Any]) -> RiskResult:
    artifact = _load_model()
    values = {
        "rainfall_mm": float(road_properties.get("rainfallMm", road_properties.get("rainfall_mm", 0))),
        "hazard_score": float(road_properties.get("hazardScore", road_properties.get("hazard_score", 0))),
        "elevation_meters": float(road_properties.get("elevationMeters", road_properties.get("elevation_meters", 0))),
        "historical_flood_exposure": float(
            road_properties.get("historicalFloodExposure", road_properties.get("historical_flood_exposure", 0))
        ),
        "drainage_pressure": float(
            road_properties.get("drainagePressure", road_properties.get("drainage_pressure", 0))
        ),
    }
    frame = pd.DataFrame([[values[name] for name in artifact["features"]]], columns=artifact["features"])
    probability = float(artifact["model"].predict_proba(artifact["scaler"].transform(frame))[0, 1])
    if probability < 0.25:
        level = "low"
    elif probability < 0.5:
        level = "medium"
    elif probability < 0.75:
        level = "high"
    else:
        level = "critical"
    base_time = float(road_properties.get("travelTimeMinutes", 10))
    delay = round(base_time * probability * (3.5 if level == "critical" else 2))
    factors = []
    if values["rainfall_mm"] > 100:
        factors.append({"id": "high_rainfall", "label": "Heavy synthetic rainfall input"})
    if values["elevation_meters"] < 5:
        factors.append({"id": "low_elevation", "label": "Low synthetic elevation input"})
    if values["historical_flood_exposure"] > 0.5:
        factors.append({"id": "historical_risk", "label": "Synthetic historical exposure input"})
    if values["drainage_pressure"] > 0.7:
        factors.append({"id": "drainage_pressure", "label": "High synthetic drainage pressure"})
    return RiskResult(
        riskProbability=round(probability, 4),
        riskLevel=level,
        estimatedDelayMinutes=delay,
        riskFactors=factors or [{"id": "baseline", "label": "Synthetic baseline risk assessment"}],
    )
