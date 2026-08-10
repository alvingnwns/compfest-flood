import os
from pathlib import Path
from typing import Any, Dict, List

import joblib
import pandas as pd
from pydantic import BaseModel

from app.errors import ApiError

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "app" / "models"
MODEL_PATH = MODELS_DIR / "flood_risk_model.joblib"

class RiskResult(BaseModel):
    riskProbability: float
    riskLevel: str
    estimatedDelayMinutes: int
    riskFactors: List[Dict[str, str]]

_artifact = None

def _load_model():
    global _artifact
    if _artifact is None:
        if not MODEL_PATH.exists():
            raise ApiError(500, "model_missing", "Flood risk model artifact not found.")
        _artifact = joblib.load(MODEL_PATH)
    return _artifact

def predict_risk(road_properties: Dict[str, Any]) -> RiskResult:
    """
    Predicts the flood disruption risk for a given road segment.
    """
    artifact = _load_model()
    model = artifact["model"]
    scaler = artifact["scaler"]
    features = artifact["features"]

    # Extract required features, substituting defaults if missing
    feature_values = {
        "rainfall_mm": float(road_properties.get("rainfallMm", 0.0)),
        "hazard_score": float(road_properties.get("hazardScore", 0.0)),
        "elevation_meters": float(road_properties.get("elevationMeters", 0.0)),
        "historical_flood_exposure": float(road_properties.get("historicalFloodExposure", 0.0)),
        "drainage_pressure": float(road_properties.get("drainagePressure", 0.0))
    }
    
    # Alternatively, road_properties might use pythonic snake_case if called internally differently,
    # but the geojson uses camelCase in 'properties'. We support snake_case as fallback.
    for k in feature_values:
        if feature_values[k] == 0.0 and k in road_properties:
            feature_values[k] = float(road_properties[k])

    df = pd.DataFrame([feature_values])
    X_scaled = scaler.transform(df)

    prob = model.predict_proba(X_scaled)[0, 1]
    
    # Determine risk level based on probability thresholds
    if prob < 0.25:
        risk_level = "low"
    elif prob < 0.5:
        risk_level = "medium"
    elif prob < 0.75:
        risk_level = "high"
    else:
        risk_level = "critical"

    # Estimate delay (synthetic logic based on prob and travelTime)
    base_travel_time = float(road_properties.get("travelTimeMinutes", 10.0))
    delay_multiplier = prob * 2.0  # max 200% delay
    if risk_level == "critical":
        delay_multiplier += 1.5
    estimated_delay = int(base_travel_time * delay_multiplier)

    # Explainability factors
    risk_factors = []
    if feature_values["rainfall_mm"] > 100:
        risk_factors.append({"id": "high_rainfall", "label": "Heavy rainfall detected"})
    if feature_values["elevation_meters"] < 5:
        risk_factors.append({"id": "low_elevation", "label": "Low elevation area"})
    if feature_values["historical_flood_exposure"] > 0.5:
        risk_factors.append({"id": "historical_risk", "label": "Historical flood exposure"})
    if feature_values["drainage_pressure"] > 0.7:
        risk_factors.append({"id": "drainage_pressure", "label": "High drainage pressure"})

    if not risk_factors:
        risk_factors.append({"id": "baseline", "label": "Baseline risk assessment"})

    return RiskResult(
        riskProbability=round(prob, 2),
        riskLevel=risk_level,
        estimatedDelayMinutes=estimated_delay,
        riskFactors=risk_factors
    )
