from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.errors import ApiError

APP_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = APP_DIR / "models" / "temporal-hazard"
MODEL_PATH = MODEL_DIR / "temporal_hazard_model.joblib"
MANIFEST_PATH = MODEL_DIR / "manifest.json"
FEATURE_CONTRACT_PATH = MODEL_DIR / "feature_contract.json"


@dataclass(frozen=True)
class TemporalHazardResult:
    temporal_hazard_score: float
    probability_calibrated: bool
    model_version: str
    model_type: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _load_runtime_model() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        contract = json.loads(FEATURE_CONTRACT_PATH.read_text(encoding="utf-8"))
        if _sha256(MODEL_PATH) != manifest["modelSha256"]:
            raise ValueError("temporal model hash mismatch")
        model = joblib.load(MODEL_PATH)
        if model["sourceArtifactSha256"] != manifest["sourceArtifactSha256"]:
            raise ValueError("temporal source provenance mismatch")
        if model["representation"] != contract["representation"]:
            raise ValueError("temporal feature representation mismatch")
        if list(model["sequenceShape"]) != contract["shape"]:
            raise ValueError("temporal sequence shape mismatch")
        if model["probabilityCalibrated"] is not False:
            raise ValueError("temporal probability semantics mismatch")
        return model, manifest, contract
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ApiError(
            503,
            "TEMPORAL_MODEL_UNAVAILABLE",
            "Model temporal hazard runtime tidak tersedia atau tidak valid.",
            retryable=True,
        ) from exc


def predict_temporal_hazard(sequence: np.ndarray) -> TemporalHazardResult:
    model, manifest, contract = _load_runtime_model()
    values = np.asarray(sequence, dtype=np.float64)
    if list(values.shape) != contract["shape"] or not np.isfinite(values).all():
        raise ApiError(
            422,
            "TEMPORAL_MODEL_INPUT_INVALID",
            "Input temporal hazard harus berupa tensor finite 30x4.",
            details={"expectedShape": contract["shape"], "actualShape": list(values.shape)},
        )
    try:
        flattened = values.reshape(1, -1, order="C")
        transformed = model["scaler"].transform(flattened)
        score = float(model["estimator"].predict_proba(transformed)[0, 1])
    except Exception as exc:
        raise ApiError(
            500,
            "DYNAMIC_HAZARD_RUNTIME_ERROR",
            "Inferensi temporal hazard gagal.",
            retryable=True,
        ) from exc
    if not np.isfinite(score) or not 0 <= score <= 1:
        raise ApiError(500, "DYNAMIC_HAZARD_RUNTIME_ERROR", "Model temporal hazard menghasilkan skor tidak valid.")
    return TemporalHazardResult(
        temporal_hazard_score=score,
        probability_calibrated=False,
        model_version=manifest["modelVersion"],
        model_type=manifest["modelType"],
    )


def temporal_model_provenance() -> dict[str, Any]:
    _, manifest, contract = _load_runtime_model()
    return {
        "modelVersion": manifest["modelVersion"],
        "modelType": manifest["modelType"],
        "modelSha256": manifest["modelSha256"],
        "sourceArtifactSha256": manifest["sourceArtifactSha256"],
        "datasetManifestSha256": manifest["datasetManifestSha256"],
        "representation": contract["representation"],
        "probabilityCalibrated": False,
    }
